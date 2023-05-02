# How it works

Yjs clients connect via WebSockets to a Channels WebSocket Consumer which can perform e.g. authentication and then forwards messages via channel layer to a central worker. This worker runs in a separate process and keeps a Yjs document + awareness information for each 'room', processes synchronization and awareness updates and sends responses (single and broadcast to room) to the WebSocket consumers.

Under the hood, this project uses [`yroom`](https://github.com/stefanw/yroom/) which is a high-level Python binding to a Yjs synchronization and awareness implementation in Rust based on the [official Yjs Rust port](https://github.com/y-crdt).


## Example flow

```mermaid
sequenceDiagram
    participant Alice
    participant WebsocketConsumerA
    participant Yroom Worker
    participant WebsocketConsumerB
    participant Bob
    Alice->>+WebsocketConsumerA: connect
    WebsocketConsumerA->>+Yroom Worker: connect
    Yroom Worker->>+WebsocketConsumerA: sync1
    WebsocketConsumerA->>+Alice: forward sync1
    Alice->>+WebsocketConsumerA: sync2
    WebsocketConsumerA->>+Yroom Worker: forward sync2

    Bob->>WebsocketConsumerB: connect
    WebsocketConsumerB->>+Yroom Worker: connect
    Yroom Worker->>+WebsocketConsumerB: sync1
    WebsocketConsumerB->>+Bob: forward sync1
    Bob->>+WebsocketConsumerB: sync2
    WebsocketConsumerB->>+Yroom Worker: forward sync2
    Bob->>+WebsocketConsumerB: update from Bob
    WebsocketConsumerB->>+Yroom Worker: forward update from Bob        

    par
        Yroom Worker->>WebsocketConsumerA: broadcast update
        WebsocketConsumerA->>Alice: forward update
    and
        Yroom Worker->>WebsocketConsumerB: broadcast update
        WebsocketConsumerB->>Bob: forward update
    end
```
