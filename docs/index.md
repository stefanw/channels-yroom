# Channels-Yroom

`channels-yroom` is a Django Channels WebSocket consumer and worker for synchronizing Yjs clients. It implements the network protocol for Yjs doc synchronization and awareness updates and makes them available as Django Channels WebSocket consumer and worker.

## What does that mean?

This project allows you to use conflict-free collaboration features based on Yjs in your web app and synchronize clients with a Django backend – eliminating the need for a separate sync server.

`channels-yroom` is intended to make adding features like real-time text collaboration an easier decision for Django projects. Effort can mainly focus on client-side experience – rather than server side integration.

## The Yjs eco system

Yjs is an ecosystem based on the idea of conflict-free replicated data types (CRDTs). It has official implementations in JS and Rust, defines network encodings and synchronization and awareness exchange protocols. Many software projects build on top of this foundation to bring collaborative features into their apps.


## Install

    pip install channels-yroom


## License

MIT