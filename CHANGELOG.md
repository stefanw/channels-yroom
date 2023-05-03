# Changelog

## v0.0.3 – 3.5.2023

- Change `YroomDocument` export API:
    - Replace `get_*` with `export_*`
    - Raise `DataUnavailable` instead of returning `None`
- Change `YroomConsumer` API:
    - Change `get_room_group_name` to `get_room_name`
- Change settings to use `YROOM_SETTINGS` with per room-prefix settings
