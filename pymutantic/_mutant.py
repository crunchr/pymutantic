import contextlib
import dataclasses
import typing

from munch import Munch
from pycrdt import Doc, Map, Array, Transaction
from pydantic import BaseModel


def to_crdt(o):
    """
    Recursively converts Pydantic models, dictionaries, and lists to CRDT-compatible types.
    """
    match o:
        case BaseModel():
            return to_crdt(o.model_dump())
        case dict():
            return Map({k: to_crdt(v) for k, v in o.items()})
        case list():
            return Array([to_crdt(i) for i in o])
        case _:
            return o


class ArrayProxy(list):
    """
    A proxy list that ensures changes are propagated to the underlying CRDT array.
    """

    def __init__(self, root, *args):
        super().__init__(*args)
        self._root = root

    def append(self, item):
        super().append(item)
        self._root.append(to_crdt(item))

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self._root.__setitem__(key, to_crdt(value))

    def extend(self, value):
        super().extend(value)
        for item in value:
            self._root.append(to_crdt(item))

    def clear(self):
        super().clear()
        self._root.clear()

    def insert(self, index, object):
        super().insert(index, object)
        self._root.insert(index, to_crdt(object))

    def pop(self, index: int = -1):
        super().pop(index)
        self._root.pop(index)

    def __delitem__(self, key):
        super().__delitem__(key)
        self._root.__delitem__(key)


def wrap(root, o):
    """
    Wraps dictionaries and lists in proxies that ensure changes are propagated to the CRDT.
    """
    match o:
        case dict():

            class ModelProxy(Munch):
                def __setattr__(self, key, value):
                    super().__setattr__(key, value)
                    root[key] = to_crdt(value)

            return ModelProxy(root, **{k: wrap(root[k], v) for k, v in o.items()})
        case list():
            return ArrayProxy(root, [wrap(root[k], v) for k, v in enumerate(o)])
        case _:
            return o


Model = typing.TypeVar("Model")


@dataclasses.dataclass
class MutateContextManager(typing.Generic[Model]):
    _mutant: 'MutantModel'
    _txn: Transaction = dataclasses.field(init=False)

    def __enter__(self) -> Model:
        root = self._mutant._root
        state = Munch(self._mutant.ConcreteModel.model_validate(root.to_py()).model_dump())
        # Here we are lying to the type system - this is actually a ModelProxy
        # object, but since we went via model_validate -> model_dump it will match
        # the given schema. This is useful for example for autocomplete in your IDE
        wrapped: Model = wrap(root, state)
        self._txn = self._mutant._doc.transaction().__enter__()
        return wrapped

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._txn.__exit__(exc_type, exc_val, exc_tb)


class MutantModel(typing.Generic[Model]):
    """
    A type safe `pycrdt.Doc` ⟷ pydantic `pydantic.BaseModel` mapping with granular editing.
    """

    ROOT_KEY = "__root__"
    _doc = Doc()

    def __init__(
        self,
        *,
        update: bytes | None = None,
        updates: tuple[bytes] = (),
        state: Model | None = None,
    ):
        # Ensure only one of `update`, `updates`, or `state` is provided
        provided_args = [update is not None, bool(updates), state is not None]
        if sum(provided_args) > 1:
            raise ValueError(
                "Only one of `update`, `updates`, or `state` should be provided."
            )

        if update is not None:
            self.update = update
        if updates:
            for update in updates:
                self.update = update
        if state is not None:
            self.state = state

    @property
    def _root(self):
        """
        Get the root map of the document.
        """
        return self._doc.get(self.ROOT_KEY, type=Map)

    @property
    def update(self) -> bytes:
        """
        Get a binary update blob which represents the latest state of the CRDT.
        """
        return self._doc.get_update()

    @update.setter
    def update(self, value: bytes):
        """
        Apply a binary update blob.
        """
        self._doc.apply_update(value)

    def mutate(self) -> MutateContextManager[Model]:
        """
        Apply mutations to the root key of the document.
        """
        return MutateContextManager(self)

    @property
    def state(self) -> Model:
        """
        Get an instance of Model that represents the current state of the CRDT.
        """
        return self.ConcreteModel.model_validate(self._root.to_py())

    @state.setter
    def state(self, value: Model):
        """
        Set the current state of the CRDT from an instance Model.

        NOTE: These are not granular edits, so will overwrite any concurrent edits at
              a more granular level.
        """
        self._doc[self.ROOT_KEY] = to_crdt(value)

    @property
    def ConcreteModel(self):
        """
        Get the ConcreteModel pydantic model.
        """
        return typing.get_args(self.__orig_class__)[0]
