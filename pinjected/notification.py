def notify(text, sound='Glass') -> str:
    """
    pops up a notification with text
    :param text:
    :return: Notification result
    """
    import platform
    if not platform.system() == 'Darwin':
        return "Not supported on this platform (only macOS)"
    import os
    org = text
    text = text.replace('"', '')
    text = text.replace("'", "")
    script = f"'display notification \"{text}\" with title \"OpenAI notification\" sound name \"{sound}\"'"
    cmd = f"""osascript -e {script} """
    os.system(cmd)
    return f"Notified user with text: {org}"
