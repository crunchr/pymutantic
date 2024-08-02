# std
import dataclasses
import typing

# 3rd party
import jsonpath_ng  # type: ignore

Model = typing.TypeVar("Model")


@dataclasses.dataclass
class JsonPathMutator(typing.Generic[Model]):
    state: Model

    def set(self, path, value):
        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.state)

        if not matches:
            raise ValueError(f"No matches found for the given path: {path}")

        for match in matches:
            parent = match.context.value
            if isinstance(match.path, jsonpath_ng.Index):
                key = match.path.index
            elif isinstance(match.path, jsonpath_ng.Fields):
                key = match.path.fields[0]
            else:
                raise TypeError("Unsupported match path type.")

            if isinstance(parent, list):
                parent[key] = value
            elif isinstance(parent, dict):
                setattr(parent, key, value)
            else:
                raise TypeError("Unsupported parent type for JSON path edit.")

    def append(self, path: str, value: typing.Any):
        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.state)

        if not matches:
            raise ValueError(f"No matches found for the given path: {path}")

        for match in matches:
            parent = match.value
            if isinstance(parent, list):
                parent.append(value)
            else:
                raise TypeError("Append operation requires a list parent.")

    def insert(self, path: str, index: int, value: typing.Any):
        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.state)

        if not matches:
            raise ValueError(f"No matches found for the given path: {path}")

        for match in matches:
            parent = match.value
            if isinstance(parent, list):
                parent.insert(index, value)
            else:
                raise TypeError("Insert operation requires a list parent.")

    def pop(self, path: str, index: int = -1):
        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.state)

        if not matches:
            raise ValueError(f"No matches found for the given path: {path}")

        for match in matches:
            parent = match.value
            if isinstance(parent, list):
                parent.pop(index)
            else:
                raise TypeError("Pop operation requires a list parent.")

    def delete(self, path: str):
        jsonpath_expr = jsonpath_ng.parse(path)
        matches = jsonpath_expr.find(self.state)

        if not matches:
            raise ValueError(f"No matches found for the given path: {path}")

        for match in matches:
            parent = match.context.value
            if isinstance(match.path, jsonpath_ng.Index):
                key = match.path.index
            elif isinstance(match.path, jsonpath_ng.Fields):
                key = match.path.fields[0]
            else:
                raise TypeError("Unsupported match path type.")

            if isinstance(parent, list):
                del parent[key]
            elif isinstance(parent, dict):
                delattr(parent, key)
            else:
                raise TypeError("Unsupported parent type for JSON path delete.")
