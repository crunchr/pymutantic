# MutantModel: A Type-Safe CRDT Integration with Pydantic

The `MutantModel` class provides an advanced and powerful integration of Conflict-free Replicated Data Types (CRDTs) with Pydantic models. This integration allows for efficient and conflict-free data synchronization across distributed systems while maintaining the benefits of Pydantic's data validation and settings management. Users can interact with the underlying CRDT structure as if it were a (potentially nested) pydantic Model, this gives some nice benefits like type checking and IDE autocompletion. This document contains some more details about the implementation and design descisions.

## Core Concepts

### CRDTs (Conflict-free Replicated Data Types):

CRDTs are data structures that allow for conflict-free merging of concurrent updates in distributed systems. This makes them ideal for collaborative applications and distributed databases. Pymutantic is built on top of pycrdt, and is designed to work with a yjs CRDT data structure. Please see [yjs](https://github.com/yjs/yjs) and [pycrdt](https://github.com/jupyter-server/pycrdt) for more details.

### Pydantic Models:

[Pydantic models](https://docs.pydantic.dev/latest/concepts/models/) provide robust data validation and settings management using Python type hints. They ensure that the data conforms to the specified schema, making it easier to manage and maintain.

### Granular Edits:

Granular edits allow for fine-grained updates to the data structure, ensuring that only the parts of the data that have changed are updated. This minimizes the amount of data that needs to be synchronized across distributed systems.

## Design Overview

The MutantModel class maps a CRDT document to a Pydantic model, ensuring that changes to the Pydantic model are propagated as granular edits to the underlying CRDT. This integration provides a powerful combination of data validation, conflict-free synchronization, and fine-grained data updates.

### Conversion to CRDT-Compatible Types:

The `to_crdt` function recursively converts Pydantic models, dictionaries, and lists to CRDT-compatible types (i.e., Map and Array). This ensures that the entire data structure can be managed as a CRDT.

### Proxy Classes for Lists and Dictionaries:

The ArrayProxy and ModelProxy classes act as intermediaries that ensure changes to lists and dictionaries are propagated to the underlying CRDT. This allows for seamless integration with standard Python data structures.

### Transactional Mutations:

The MutateInTransaction class provides a context manager for applying mutations within a transaction. The result of the `__enter__` function contains the instance data from the CRDT which is to be edited. This context manager is also responsible for fooling the type system into thinking it is receiving an instance of a pydantic model. In reality it is will be nested Proxy classes that synchronise edits to the underlying CRDT. In this manner the user can edit the received object as if it were an instance of the underlying pydantic Model. All operations are grouped into a yjs transaction. 

### State Management

The MutantModel class provides properties and methods for getting and setting the state of the CRDT as an instance of the Pydantic model that is given as a type parameter. It also ensures that the state transitions are type-safe and validated.
Granular Update Handling:

By wrapping lists and dictionaries in proxy objects, the `MutantModel` class ensures that updates to individual elements are propagated as granular edits to the CRDT. This allows for efficient synchronization of changes across distributed systems.