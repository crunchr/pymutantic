# std
import dataclasses
import typing

# 1st party
from pymutantic.mutant import MutantModel


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
class Migration:
    model_versions: list[typing.Type[VersionProtocol]]
    instance: MutantModel

    def to(self, /, to: typing.Type[To]) -> MutantModel[To]:
        """
        Migrate self.instance to the given model version.
        """
        from_version_index = self.model_versions.index(self.instance.ConcreteModel)
        to_version_index = self.model_versions.index(to)

        if from_version_index < to_version_index:
            # Upgrade
            slicer = slice(from_version_index + 1, to_version_index + 1)
            direction = 1
        else:
            # Downgrade
            slicer = slice(from_version_index, to_version_index, -1)
            direction = -1

        with self.instance.mutate() as state:
            for ModelVersion in self.model_versions[slicer]:
                fn = ModelVersion.up if direction == 1 else ModelVersion.down
                fn(state, state)
                state.schema_version += direction

        result = MutantModel[To](update=self.instance.update)
        result.ConcreteModel = to

        return result


@dataclasses.dataclass
class MigrationChain:
    model_versions: list[typing.Type[VersionProtocol]]

    def __call__(self, instance: MutantModel):
        return Migration(self.model_versions, instance)
