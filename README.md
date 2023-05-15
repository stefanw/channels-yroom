# Channels-Yroom

![PyPI](https://img.shields.io/pypi/v/channels-yroom)

`channels-yroom` is a Django Channels WebSocket consumer and worker for synchronizing Yjs clients. It implements the network protocol for Yjs doc synchronization and awareness updates and makes them available as Django Channels WebSocket consumer and worker.

## Documentation

[Read the documentation](https://channels-yroom.readthedocs.io/en/latest/)

## Showcase: text collaboration example

The `example` folder contains a simple project that uses `y-prosemirror` to allow for realtime collaboration on rich text.

Run the included Docker compose file to check it out:

```sh
docker compose up
# Then visit localhost:8000
```

## Development

Project uses `hatch` for the development workflow:

```
pip install hatch

hatch run +py=3.10 test:test
```

## License

MIT
