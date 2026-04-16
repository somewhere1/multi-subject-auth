from user_agents import parse


def parse_device_name(user_agent: str) -> str:
    ua = parse(user_agent)
    browser = ua.browser.family
    os_name = ua.os.family
    if browser and os_name:
        return f"{browser} on {os_name}"
    if browser:
        return browser
    return "Unknown Device"
