# std
import typing

# 3rd party
import pytest
from pydantic import BaseModel

# 1st party
from pymutantic.migrate import ModelVersionRegistry
from pymutantic.mutant import MutantModel


class ModelV1(BaseModel):
    schema_version: int = 1
    field: str
    some_field: str

    @classmethod
    def up(cls, state: typing.Any, new_state: typing.Any):
        raise NotImplementedError("can't migrate from null version")

    @classmethod
    def down(cls, state: typing.Any, new_state: typing.Any):
        raise NotImplementedError("can't migrate to null version")


class ModelV2(BaseModel):
    schema_version: int = 2
    some_field: str

    @classmethod
    def up(cls, state: ModelV1, new_state: "ModelV2"):
        del state.field

    @classmethod
    def down(cls, state: "ModelV2", new_state: ModelV1):
        new_state.field = "default"  # Adding a default value for demonstration


class ModelV3(BaseModel):
    schema_version: int = 3
    some_field: str
    some_new_field: float

    @classmethod
    def up(cls, state: ModelV2, new_state: "ModelV3"):
        new_state.some_new_field = 42.0

    @classmethod
    def down(cls, state: "ModelV3", new_state: ModelV2):
        del state.some_new_field


class ModelV4(BaseModel):
    schema_version: int = 4
    some_field: str
    some_new_field: float
    another_new_field: bool

    @classmethod
    def up(cls, state: ModelV3, new_state: "ModelV4"):
        new_state.another_new_field = True

    @classmethod
    def down(cls, state: "ModelV4", new_state: ModelV3):
        del state.another_new_field


class ModelV5(BaseModel):
    schema_version: int = 5
    some_field: str
    some_new_field: float
    another_new_field: bool
    yet_another_field: int

    @classmethod
    def up(cls, state: ModelV4, new_state: "ModelV5"):
        new_state.yet_another_field = 100

    @classmethod
    def down(cls, state: "ModelV5", new_state: ModelV4):
        del state.yet_another_field


migrate = ModelVersionRegistry([ModelV1, ModelV2, ModelV3, ModelV4, ModelV5]).migrate


def test_migration_v1_to_v3():
    doc = MutantModel[ModelV1](state=ModelV1(field="hello", some_field="world"))
    doc = migrate(doc, to=ModelV3)
    assert doc.snapshot.schema_version == 3
    assert doc.snapshot.some_field == "world"
    assert doc.snapshot.some_new_field == 42.0


def test_migration_v3_to_v1():
    doc = MutantModel[ModelV3](state=ModelV3(some_field="world", some_new_field=42.0))
    doc = migrate(doc, to=ModelV1)
    assert doc.snapshot.schema_version == 1
    assert doc.snapshot.field == "default"  # Default value added in down migration
    assert doc.snapshot.some_field == "world"


def test_migration_v2_to_v4():
    doc = MutantModel[ModelV2](state=ModelV2(some_field="world"))
    doc = migrate(doc, to=ModelV4)
    assert doc.snapshot.schema_version == 4
    assert doc.snapshot.some_field == "world"
    assert doc.snapshot.some_new_field == 42.0
    assert doc.snapshot.another_new_field is True


def test_downgrade_v4_to_v2():
    doc = MutantModel[ModelV4](
        state=ModelV4(some_field="world", some_new_field=42.0, another_new_field=True)
    )
    doc = migrate(doc, to=ModelV2)
    assert doc.snapshot.schema_version == 2
    assert doc.snapshot.some_field == "world"


def test_migration_v3_to_v5():
    doc = MutantModel[ModelV3](state=ModelV3(some_field="world", some_new_field=42.0))
    doc = migrate(doc, to=ModelV5)
    assert doc.snapshot.schema_version == 5
    assert doc.snapshot.some_field == "world"
    assert doc.snapshot.some_new_field == 42.0
    assert doc.snapshot.another_new_field is True
    assert doc.snapshot.yet_another_field == 100


def test_downgrade_v5_to_v3():
    doc = MutantModel[ModelV5](
        state=ModelV5(
            some_field="world",
            some_new_field=42.0,
            another_new_field=True,
            yet_another_field=100,
        )
    )
    doc = migrate(doc, to=ModelV3)
    assert doc.snapshot.schema_version == 3
    assert doc.snapshot.some_field == "world"
    assert doc.snapshot.some_new_field == 42.0


def test_concurrent_edit_during_migration():
    doc_v1 = MutantModel[ModelV1](state=ModelV1(field="hello", some_field="world"))

    # Make an independent edit
    doc_v1_copy = MutantModel[ModelV1](update=doc_v1.update)
    with doc_v1_copy.mutate() as state:
        state.some_field = "earth"

    # Migrate the original document to V5
    doc_v5 = migrate(doc_v1, to=ModelV5)
    assert doc_v5.snapshot.schema_version == 5
    assert doc_v5.snapshot.some_field == "world"
    assert doc_v5.snapshot.some_new_field == 42.0
    assert doc_v5.snapshot.another_new_field is True
    assert doc_v5.snapshot.yet_another_field == 100

    # Apply the independent edit to the migrated document
    doc_v5_with_edit = MutantModel[ModelV5](updates=(doc_v5.update, doc_v1_copy.update))
    assert doc_v5_with_edit.snapshot.schema_version == 5
    assert doc_v5_with_edit.snapshot.some_field == "earth"
    assert doc_v5_with_edit.snapshot.some_new_field == 42.0
    assert doc_v5_with_edit.snapshot.another_new_field is True
    assert doc_v5_with_edit.snapshot.yet_another_field == 100


if __name__ == "__main__":
    pytest.main([__file__])
