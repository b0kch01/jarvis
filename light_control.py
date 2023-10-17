from govee_api_laggat import Govee


async def get_lights(govee: Govee):
    cache_devices = govee.devices

    if not cache_devices:
        print("-- No devices found, trying to load them...")
        cache_devices, _ = await govee.get_devices()

    names = ["Small Lamp", "Bar",
             #  "Bulb A", "Bulb B", "Bulb C"
             ]
    return list(filter(lambda x: x.device_name in names, cache_devices))


async def turn_off_lights(govee: Govee):
    for device in await get_lights(govee):
        await govee.turn_off(device)


async def warm_lights(govee: Govee):
    for device in await get_lights(govee):
        if device.device_name == "Bar":
            await govee.set_color_temp(device, 2000)
        else:
            await govee.set_color_temp(device, 2700)
