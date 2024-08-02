# std
import dataclasses
import typing

# 1st party
from pymutantic._mutant import MutantModel


class VersionProtocol(typing.Protocol):
    schema_version: int

    @classmethod
    def up(cls, state: typing.Any, new_state: typing.Any):
        pass

    @classmethod
    def down(cls, state: typing.Any, new_state: typing.Any):
        pass


To = typing.TypeVar("To", bound=VersionProtocol)


@dataclasses.dataclass
class ModelVersionRegistry:
    model_versions: list[typing.Type[VersionProtocol]]

    def migrate(self, instance: MutantModel, *, to: typing.Type[To]) -> MutantModel[To]:

        from_version_index = self.model_versions.index(instance.PydanticModel)
        to_version_index = self.model_versions.index(to)

        if from_version_index < to_version_index:
            slicer = slice(from_version_index + 1, to_version_index + 1)
            direction = 1
        else:
            slicer = slice(from_version_index, to_version_index, -1)
            direction = -1

        with instance.mutate() as state:
            for ModelVersion in self.model_versions[slicer]:
                fn = ModelVersion.up if direction == 1 else ModelVersion.down
                fn(state, state)
                state.schema_version += direction

        result = MutantModel[To](update=instance.update)
        result.PydanticModel = to

        return result
