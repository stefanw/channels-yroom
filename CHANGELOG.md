# Changelog


## v0.0.5 – 16.5.2023

- Add setting to disable pipelining of messages for TipTap integration
- Fix bug where missing connect message would reset room
- Use existing Websocket consumer channel for communication from `yroom` worker. Before an extra channel was used.

## v0.0.4 – 4.5.2023

- Fix bad worker configuration

## v0.0.3 – 3.5.2023

- Change `YroomDocument` export API:
    - Replace `get_*` with `export_*`
    - Raise `DataUnavailable` instead of returning `None`
- Change `YroomConsumer` API:
    - Change `get_room_group_name` to `get_room_name`
- Change settings to use `YROOM_SETTINGS` with per room-prefix settings
