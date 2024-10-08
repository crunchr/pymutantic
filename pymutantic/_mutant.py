# std
import dataclasses
import typing

# 3rd party
from munch import Munch  # type: ignore
from pycrdt import Array, Doc, Map, Transaction
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

    def pop(self, index: typing.SupportsIndex = -1):
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


PydanticModel = typing.TypeVar("PydanticModel")


@dataclasses.dataclass
class MutateInTransaction(typing.Generic[PydanticModel]):
    _mutant: "MutantModel"
    _txn: Transaction = dataclasses.field(init=False)

    def __enter__(self) -> PydanticModel:
        root = self._mutant._root
        state = Munch(
            self._mutant.PydanticModel.model_validate(root.to_py()).model_dump()
        )
        # Here we are lying to the type system - this is actually a ModelProxy
        # object, but since we went via model_validate -> model_dump it will match
        # the given model. This is useful for example for autocomplete in your IDE
        wrapped: PydanticModel = wrap(root, state)
        self._txn = self._mutant._doc.transaction().__enter__()
        return wrapped

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._txn.__exit__(exc_type, exc_val, exc_tb)


class MutantModel(typing.Generic[PydanticModel]):
    """
    A type safe `pycrdt.Doc` ⟷ pydantic `pydantic.BaseModel` mapping with granular editing.
    """

    ROOT_KEY = "__root__"

    def __init__(
        self,
        *,
        update: bytes | None = None,
        updates: tuple[bytes, ...] = (),
        state: PydanticModel | None = None,
    ):
        self._doc = Doc()
        self._PydanticModel = None

        # Ensure only one of `update`, `updates`, or `state` is provided
        provided_args = [update is not None, bool(updates), state is not None]
        if sum(provided_args) > 1:
            raise ValueError(
                "Only one of `update`, `updates`, or `state` should be provided."
            )

        if update is not None:
            self.apply_updates(update)
        if updates:
            self.apply_updates(*updates)
        if state is not None:
            self.set_state(state)

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

    def apply_updates(self, *values: bytes):
        """
        Apply a binary update blob.
        """
        for value in values:
            self._doc.apply_update(value)

    def mutate(self) -> MutateInTransaction[PydanticModel]:
        """
        Apply mutations to the root key of the document.
        """
        return MutateInTransaction(self)

    @property
    def snapshot(self) -> PydanticModel:
        """
        Get an instance of Model that represents the current state of the CRDT.
        """
        return self.PydanticModel.model_validate(self._root.to_py())

    def set_state(self, value: PydanticModel):
        """
        Set the current state of the CRDT from an instance Model.

        NOTE: These are not granular edits, so will overwrite any concurrent edits at
              a more granular level.
        """
        self._doc[self.ROOT_KEY] = to_crdt(value)

    @property
    def PydanticModel(self):
        """
        Get the PydanticModel pydantic model.
        """
        if self._PydanticModel is None:
            assert hasattr(self, "__orig_class__")
            return typing.get_args(self.__orig_class__)[0]
        else:
            return self._PydanticModel

    @PydanticModel.setter
    def PydanticModel(self, value):
        """
        Set the PydanticModel pydantic model.

        Mostly the PydanticModel should come from a type parameter
        e.g. MutantModel[MyModel] but sometimes the exact model might be
        dynamic, and so cannot be used as a type parameter.
        """
        self._PydanticModel = value
