import asyncio
import copy
import os
import subprocess
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from pprint import pformat

import PIL.Image
import pyautogui
from anthropic import Anthropic
from anthropic.types.beta import (
    BetaMessage,
    BetaTextBlock,
    BetaToolUseBlock,
    BetaUsage,
)
from pinjected_anthropic.llm import anthropic_client, image_to_base64

from pinjected import *


class ChromeActivationError(Exception):
    """Custom exception for Chrome activation errors"""


class ScreenshotError(Exception):
    """Custom exception for screenshot errors"""





@dataclass
class BrowserBBox:
    """Represents the bounding box of the browser window on screen"""
    x: int
    y: int
    width: int
    height: int

    def contains_point(self, point: tuple[int, int]) -> bool:
        """Check if a point is within the bounding box"""
        px, py = point
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def to_screen_coordinates(self, x: int, y: int) -> tuple[int, int]:
        """
        Convert coordinates relative to the browser window to screen coordinates

        Args:
            x: X coordinate relative to browser window's top-left corner
            y: Y coordinate relative to browser window's top-left corner

        Returns:
            Tuple[int, int]: Screen coordinates (x, y)
        """
        screen_x = self.x + x
        screen_y = self.y + y
        return (screen_x, screen_y)

    def to_local_coordinates(self, screen_x: int, screen_y: int) -> tuple[int, int]:
        """
        Convert screen coordinates to coordinates relative to browser window

        Args:
            screen_x: X coordinate in screen space
            screen_y: Y coordinate in screen space

        Returns:
            Tuple[int, int]: Local coordinates (x, y) relative to window
        """
        local_x = screen_x - self.x
        local_y = screen_y - self.y
        return (local_x, local_y)


@injected
def get_chrome_bbox() -> BrowserBBox:
    """
    Gets the current position and size of the Chrome window.
    We use @injected since we want to dynamically get value everytime we call this.
    Returns:
        BrowserBBox: Dataclass containing window bounds

    Raises:
        ChromeActivationError: If Chrome window info can't be retrieved
        OSError: If not running on macOS
    """
    apple_script = """
    tell application "Google Chrome"
        tell application "System Events"
            set chromeWindow to first window of application process "Google Chrome"
            return {position, size} of chromeWindow
        end tell
    end tell
    """

    try:
        result = subprocess.run(['osascript', '-e', apple_script],
                                capture_output=True, text=True, check=True)
        # Parse AppleScript output which looks like "{{x, y}, {width, height}}"
        output = result.stdout.strip()
        # Remove curly braces and split by comma
        nums = [int(n) for n in output.replace('{', '').replace('}', '').split(', ')]
        return BrowserBBox(x=nums[0], y=nums[1], width=nums[2], height=nums[3])
    except subprocess.CalledProcessError as e:
        raise ChromeActivationError(f"Failed to get Chrome window bounds: {e.stderr}")
    except (ValueError, IndexError) as e:
        raise ChromeActivationError(f"Failed to parse Chrome window bounds: {e}")
    except FileNotFoundError:
        raise OSError("This script requires macOS and osascript to run")


@injected
def bring_chrome_to_front():
    """
    Brings Google Chrome to the foreground on macOS with forced keyboard focus.

    Raises:
        ChromeActivationError: If there's an error activating Chrome
        OSError: If not running on macOS or osascript is not available
    """
    apple_script = """
    tell application "Google Chrome"
        activate
    end tell
    
    delay 0.1
    
    tell application "System Events"
        set chromeProcess to first process whose name is "Google Chrome"
        set frontmost of chromeProcess to true
        
        tell process "Google Chrome"
            set frontWindow to first window
            # Try multiple focus methods
            set focused of frontWindow to true
            perform action "AXRaise" of frontWindow
            click frontWindow
            
            # Force keyboard focus to the window content
            try
                set webView to first UI element of frontWindow whose role description contains "web"
                set focused of webView to true
            end try
        end tell
    end tell
    
    # One more activate for good measure
    tell application "Google Chrome"
        activate
    end tell
    """

    try:
        subprocess.run(['osascript', '-e', apple_script], check=True,
                       capture_output=True, text=True)

        # Add a small delay to let focus settle
        import time
        time.sleep(0.2)
    except subprocess.CalledProcessError as e:
        raise ChromeActivationError(f"Failed to activate Chrome: {e.stderr}")
    except FileNotFoundError:
        raise OSError("This script requires macOS and osascript to run")


@injected
def take_chrome_screenshot(
        bring_chrome_to_front,
        get_chrome_bbox,
        logger,
        /,
        output_path: Path | None = "last_screenshot.png",
        include_cursor: bool = True) -> tuple[PIL.Image.Image, BrowserBBox]:
    """
    Takes a screenshot of the Chrome window and returns it as a PIL Image.

    Args:
        output_path (Path, optional): Path where to save the screenshot.
            If provided, the image will be saved there in addition to being returned.
        include_cursor (bool): Whether to include the mouse cursor in the screenshot.
            Defaults to False.

    Returns:
        Tuple[Image.Image, BrowserBBox]: PIL Image object and window bounds

    Raises:
        ChromeActivationError: If Chrome can't be activated
        ScreenshotError: If screenshot fails
        OSError: If not running on macOS
    """
    # First bring Chrome to front
    bring_chrome_to_front()

    # Wait a brief moment for window to be fully in front
    import tempfile
    import time

    from PIL import Image
    time.sleep(0.5)

    # Get the window bounds
    bbox = get_chrome_bbox()

    try:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            # Take full screenshot with cursor if requested
            cursor_flag = "-C" if include_cursor else ""
            cmd = f"screencapture {cursor_flag} '{tmp_file.name}'"
            subprocess.run(cmd, shell=True, check=True)

            # Open and crop with PIL
            image = Image.open(tmp_file.name)
            final_image = image.crop((bbox.x * 2, bbox.y * 2, (bbox.x + bbox.width) * 2, (bbox.y + bbox.height) * 2))
            final_image = final_image.resize((bbox.width, bbox.height), Image.LANCZOS)
            logger.info(f"cropped image resolution and original: {final_image.size} {image.size}")
            image.close()
            os.unlink(tmp_file.name)

        # Save to output_path if provided
        if output_path is not None:
            final_image.save(output_path)

        return final_image, bbox

    except subprocess.CalledProcessError as e:
        raise ScreenshotError(f"Failed to take screenshot: {e}")
    except OSError as e:
        raise ScreenshotError(f"Failed to process screenshot: {e}")


test_bring_chrome_to_front: IProxy = bring_chrome_to_front()
test_take_chrome_screenshot: IProxy = take_chrome_screenshot()


# now we have good screen readability. let's use cluade

@injected
def pil_image_to_image_block(img: PIL.Image.Image, img_format='jpeg'):
    if img_format == 'jpeg':
        img = img.convert('RGB')
    block = {
        'type': 'image',
        'source': {
            'type': 'base64',
            'media_type': f"image/{img_format}",
            'data': image_to_base64(img, img_format),
        }
    }
    return block


@dataclass
class RespWithBbox:
    resp: BetaMessage
    bbox: BrowserBBox


@dataclass(frozen=True)
class AnthropicToolResult:
    _pil_image_to_image_block: callable

    tool_id: str
    content: list[dict] = field(default_factory=list)
    is_error: bool = False

    def add_text(self, text: str):
        return replace(self, content=self.content + [
            {'type': 'text', 'text': text}
        ])

    def add_image(self, img: PIL.Image.Image):
        return replace(self, content=self.content + [
            self._pil_image_to_image_block(img)
        ])

    def to_tool_result_block(self):
        return {
            'type': "tool_result",
            'tool_use_id': self.tool_id,
            'content': self.content
        }


@injected
def new_AnthropicToolResult(pil_image_to_image_block, /, *args, **kwargs):
    return AnthropicToolResult(
        pil_image_to_image_block,
        *args,
        **kwargs
    )


@dataclass(frozen=True)
class AnthropicChatContext:
    """
    Immutable dataclass to hold context for an Anthropic chat session
    """
    _pil_image_to_image_block: callable
    _anthropic_client: Anthropic

    model: str
    max_tokens: int
    tools: list[dict]
    system: str
    messages: list[dict]
    betas: list[str]

    def __post_init__(self):
        self.validate()

    def validate(self):
        for c in self.messages:
            assert isinstance(c, dict)
            assert 'role' in c, f"role not in message: {c}"
            assert 'content' in c, f"content not in message: {c}"
            assert isinstance(c['content'], list), f"content is not a list: {c['content']}"

    def add_message(self, role: str, content: str):
        assert isinstance(content, str)
        new_self = replace(self,
                           messages=self.messages + [{"role": role, "content": [{"type": "text", "text": content}]}])
        new_self.validate()
        return new_self

    def add_tool_result(self, tool_result: AnthropicToolResult):
        return replace(self, messages=self.messages + [
            {
                "role": "user",
                "content": [tool_result.to_tool_result_block()]
            }
        ])

    def add_image_message(self, role: str, img: PIL.Image.Image):
        # self.messages.append({"role": role, "content": [self._pil_image_to_image_block(img)]})
        return replace(self,
                       messages=self.messages + [{"role": role, "content": [self._pil_image_to_image_block(img)]}])

    def add_tool_use(self, use: BetaToolUseBlock):
        return replace(self,
                       messages=self.messages + [{"role": "assistant", "content": [{
                           'id': use.id,
                           'input': use.input,
                           'name': use.name,
                           'type': use.type,
                       }]}])

    def set_display_size(self, width: int, height):
        def is_computer(tool):
            return 'type' in tool and tool['type'] == 'computer_20241022'

        display_tool = next((t for t in self.tools if is_computer(t)), None)
        other_tools = [t for t in self.tools if not is_computer(t)]
        if display_tool:
            new_display_tool = copy.deepcopy(display_tool)
            new_display_tool['display_width_px'] = width
            new_display_tool['display_height_px'] = height
            return replace(self, tools=other_tools + [new_display_tool])
        new_display_tool = {
            "type": "computer_20241022",
            "name": "computer",
            "display_width_px": width,
            "display_height_px": height,
            "display_number": 1,
        }
        return replace(self, tools=other_tools + [new_display_tool])

    async def acall(self):
        return await self._anthropic_client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=self.tools,
            system=self.system,
            messages=self.messages,
            betas=self.betas,
        )

    def truncate_image_data(self):
        return self

    def __str_impl__(self):
        return pformat(self.__dict__)

    def __repr_impl__(self):
        return pformat(self.__dict__)

    def __str__(self):
        return self.truncate_image_data().__str_impl__()

    def __repr__(self):
        return self.truncate_image_data().__repr_impl__()


@injected
async def a_add_chrome_screenshot_cxt(
        take_chrome_screenshot,
        /,
        cxt: AnthropicChatContext):
    screenshot, bbox = take_chrome_screenshot(include_cursor=True)
    assert screenshot.size == (bbox.width, bbox.height), f"Screenshot size mismatch: {screenshot.size} vs {bbox}"
    cxt = cxt.add_image_message("user", screenshot)
    cxt = cxt.set_display_size(bbox.width, bbox.height)
    return cxt, bbox


@injected
async def a_chrome_screenshot(
        take_chrome_screenshot,
        new_AnthropicToolResult,
        /,
        tool_id: str):
    screenshot, bbox = take_chrome_screenshot(include_cursor=True)
    return new_AnthropicToolResult(tool_id=tool_id).add_image(screenshot), bbox


@injected
def new_AnthropicChatContext(pil_image_to_image_block, anthropic_client, /, **kwargs):
    return AnthropicChatContext(
        pil_image_to_image_block,
        anthropic_client,
        **kwargs
    )


@injected
def set_chrome_window_size(width: int, height: int, x: int | None = None, y: int | None = None) -> BrowserBBox:
    """
    Sets the Chrome window size and optionally its position.

    Args:
        width: Desired window width in pixels
        height: Desired window height in pixels
        x: Optional x position for the window. If None, keeps current x position
        y: Optional y position for the window. If None, keeps current y position

    Returns:
        BrowserBBox: The new window bounds after resizing

    Raises:
        ChromeActivationError: If Chrome window can't be modified
        OSError: If not running on macOS
    """
    # Build the position setting part of the script conditionally
    position_script = ""
    if x is not None and y is not None:
        position_script = f"set position of chromeWindow to {{{x}, {y}}}"

    apple_script = f"""
    tell application "Google Chrome"
        tell application "System Events"
            set chromeWindow to first window of application process "Google Chrome"
            set size of chromeWindow to {{{width}, {height}}}
            {position_script}
            return {{position, size}} of chromeWindow
        end tell
    end tell
    """

    try:
        result = subprocess.run(['osascript', '-e', apple_script],
                                capture_output=True, text=True, check=True)
        # Parse AppleScript output which looks like "{{x, y}, {width, height}}"
        output = result.stdout.strip()
        # Remove curly braces and split by comma
        nums = [int(n) for n in output.replace('{', '').replace('}', '').split(', ')]
        return BrowserBBox(x=nums[0], y=nums[1], width=nums[2], height=nums[3])
    except subprocess.CalledProcessError as e:
        raise ChromeActivationError(f"Failed to set Chrome window size: {e.stderr}")
    except (ValueError, IndexError) as e:
        raise ChromeActivationError(f"Failed to parse Chrome window bounds: {e}")
    except FileNotFoundError:
        raise OSError("This script requires macOS and osascript to run")


@instance
async def initial_cxt(new_AnthropicChatContext):
    return new_AnthropicChatContext(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=[
            {
                "type": "computer_20241022",
                "name": "computer",
                "display_width_px": 1024,
                "display_height_px": 768,
                "display_number": 1,
            },
            {
                "type": "text_editor_20241022",
                "name": "str_replace_editor"
            },
            {
                "type": "bash_20241022",
                "name": "bash"
            },
            {
                "name": "wait",
                'description': 'Wait for specified seconds to pass. Useful for waiting other tools to finish',
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "seconds": {
                            "type": "number",
                            "description": "Number of seconds to wait"
                        }
                    },
                    "required": ["seconds"]
                }
            },
        ],
        betas=["computer-use-2024-10-22"],
        system="The user's computer is MacOS. Google Chrome is already opened and preferred for use.",
        messages=[]
    )


@injected
def show_cxt__rich(cxt: AnthropicChatContext):
    from rich import print
    print(f"-------- Log Visualizer -------")
    cxt = cxt.truncate_image_data()
    # show tools
    print(f"[bold]Tools:[/bold]")
    for tool in cxt.tools:
        print(f"[bold]{tool['name']}[/bold]")
        for k, v in tool.items():
            print(f"{k}: {v}")

    for msg in cxt.messages:
        role = msg['role']
        color = 'blue' if role == 'user' else 'green'

        def print_block(block):
            match block:
                case {'type': 'text', 'text': text}:
                    print(f"[{color}]{role}: {text}")
                case {'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': data}}:
                    print(f"[{color}]{role}: Image ({media_type})")
                case {'type': 'tool_result', 'tool_use_id': tool_use_id, 'content': content}:
                    for cnt in content:
                        print_block(cnt)
                case blk:
                    print(f"[{color}]{role}: Unhandled -> {blk}")

        for block in msg['content']:
            print_block(block)


@injected
async def a_handle_str_replace_editor(
        logger,
        new_AnthropicToolResult,
        /,
        cxt: AnthropicChatContext,
        tool_use: BetaToolUseBlock,
) -> AnthropicChatContext:
    """
ファイルの表示、作成、編集のためのカスタム編集ツール
* 状態はコマンド呼び出しとユーザーとの対話全体で永続的です
* `path`がファイルの場合、`view`は`cat -n`の結果を表示します。`path`がディレクトリの場合、`view`は2レベルまでの非表示ファイルとディレクトリをリストアップします
* `create`コマンドは、指定された`path`が既にファイルとして存在する場合は使用できません
* `command`が長い出力を生成する場合、切り詰められ、`<response clipped>`とマークされます
* `undo_edit`コマンドは、`path`のファイルに対して行われた最後の編集を元に戻します

`str_replace`コマンドを使用する際の注意点：
* `old_str`パラメータは、元のファイルから1行以上の連続した行と正確に一致する必要があります。空白に注意してください！
* `old_str`パラメータがファイル内で一意でない場合、置換は実行されません。`old_str`を一意にするために十分なコンテキストを含めてください
* `new_str`パラメータには、`old_str`を置き換えるべき編集された行を含める必要があります
"""
    cxt = cxt.add_tool_use(tool_use)
    match tool_use.input:
        case {'command': 'create', 'path': path, 'file_text': file_text}:
            logger.info(f"Creating file at {path}")
            Path(path).write_text(file_text)
            cxt = cxt.add_tool_result(new_AnthropicToolResult(tool_use.id).add_text(f"Created file at {path}"))
        case {'command': 'view', 'path': path}:
            path = Path(path)
            if path.is_file():
                logger.info(f"Viewing file at {path}")
                cxt = cxt.add_tool_result(new_AnthropicToolResult(tool_use.id).add_text(path.read_text()))
        case {'command': 'str_replace', 'path': path, 'old_str': old, 'new_str': new}:
            text = Path(path).read_text()
            import pandas as pd
            Path(path).with_suffix(f'.{pd.Timestamp.now().strftime("%Y%m%d%H%M%S")}.bak').write_text(text)
            new_text = text.replace(old, new)
            Path(path).write_text(new_text)
            logger.warning(f"Replaced {old} with {new} in {path}")
            cxt = cxt.add_tool_result(new_AnthropicToolResult(tool_use.id).add_text(f"Replaced {old} with {new}"))
        case {'command': 'undo_edit', 'path': path}:
            raise RuntimeError(f"Not implemented: {tool_use}")
        case _:
            raise ValueError(f"Unknown str_replace_tool input: {tool_use.input}")
    return cxt


@injected
async def a_handle_bash(
        logger,
        new_AnthropicToolResult,
        /,
        cxt: AnthropicChatContext,
        tool_use: BetaToolUseBlock,
):
    """
    Run commands in a bash shell
* When invoking this tool, the contents of the "command" parameter does NOT need to be XML-escaped.
* You have access to a mirror of common linux and python packages via apt and pip.
* State is persistent across command calls and discussions with the user.
* To inspect a particular line range of a file, e.g. lines 10-25, try 'sed -n 10,25p /path/to/the/file'.
* Please avoid commands that may produce a very large amount of output.
* Please run long lived commands in the background, e.g. 'sleep 10 &' or start a server in the background.
    :return:
    """
    cxt = cxt.add_tool_use(tool_use)
    match tool_use.input:
        case {'command': command}:
            logger.info(f"Running command: {command}")
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
                cxt = cxt.add_tool_result(new_AnthropicToolResult(tool_use.id).add_text(result.stdout))
            except subprocess.CalledProcessError as e:
                cxt = cxt.add_tool_result(new_AnthropicToolResult(tool_use.id).add_text(e.stderr))
        case _:
            raise ValueError(f"Unknown bash tool input: {tool_use.input}")
    return cxt


class AnthropicAutomationException(Exception):
    pass


class AnthropicAutomationDown(Exception):
    pass


@injected
async def a_handle_action_loop(
        anthropic_client: Anthropic,
        logger,
        a_chrome_screenshot,
        initial_cxt: AnthropicChatContext,
        a_add_chrome_screenshot_cxt,
        new_AnthropicToolResult,
        show_cxt__rich,
        a_send_hotkey,
        set_chrome_window_size,
        a_handle_str_replace_editor,
        a_handle_bash,
        /,
        initial_msg: str,
        wait_user_input: bool = False,
) -> AnthropicChatContext:
    """
    TODO use VNC to use remote PC, so that a user can keep his work...
    """
    cxt = initial_cxt
    last_bbox: BrowserBBox = None
    set_chrome_window_size(1024, 768)
    cxt = cxt.add_message("user", initial_msg)
    logger.info(f"Initial context: {cxt}")
    cost_usd = 0
    cum_price_usd = 0
    usage: BetaUsage = None
    block_n = 0
    block_i = 0

    def show_usage():
        import rich
        rich.print(f"[bold orange]Cost: {cost_usd:.2f} USD, Cumulative: {cum_price_usd:.2f} USD[/bold orange]")
        rich.print(f"[bold orange]Last Usage: {usage}[/bold orange]")

    def on_cxt_update(cxt: AnthropicChatContext):
        show_cxt__rich(cxt)
        show_usage()
        import rich
        rich.print(f"[bold]Block {block_i}/{block_n}[/bold]")

    async def handle_block(cnt) -> AnthropicChatContext:
        nonlocal last_bbox, cxt
        match cnt:
            case BetaTextBlock(text=text, type=_):
                logger.info(f"Message: {text}")
                cxt = cxt.add_message("assistant", text)
                on_cxt_update(cxt)
            case BetaToolUseBlock(id=_id, input=_input, name='wait', type=_) as use:
                cxt = cxt.add_tool_use(use)
                on_cxt_update(cxt)
                match _input:
                    case {'seconds': seconds}:
                        logger.info(f"Waiting for {seconds} seconds")
                        await asyncio.sleep(seconds)
                    case _:
                        raise ValueError(f"Unknown wait input: {_input}")
                cxt = cxt.add_tool_result(new_AnthropicToolResult(_id).add_text(f"Waited for {seconds} seconds"))
                on_cxt_update(cxt)
            case BetaToolUseBlock(id=_id, input=_input, name='str_replace_editor', type=_) as use:
                cxt = await a_handle_str_replace_editor(cxt, use)
                on_cxt_update(cxt)
            case BetaToolUseBlock(id=_id, input=_input, name='bash', type=_) as use:
                cxt = await a_handle_bash(cxt, use)
                on_cxt_update(cxt)
            case BetaToolUseBlock(id=_id, input=_input, name='computer', type=_) as use:
                cxt = cxt.add_tool_use(use)
                on_cxt_update(cxt)
                match _input:
                    case {'action': 'mouse_move', 'coordinate': (x, y)}:
                        screen_x, screen_y = last_bbox.to_screen_coordinates(x, y)
                        pyautogui.moveTo(screen_x, screen_y)
                        logger.info(f"Mouse moved to {x},{y} ({screen_x},{screen_y})")
                        tool_result = new_AnthropicToolResult(tool_id=_id).add_text(f"Mouse moved to {x},{y}")
                        cxt = cxt.add_tool_result(tool_result)
                    case {'action': 'left_click' }:
                        logger.info(f"Mouse click.")
                        pyautogui.click()
                        cxt = cxt.add_tool_result(new_AnthropicToolResult(_id).add_text(f"Mouse clicked."))
                    case {'action': 'right_click', 'coordinate': (x, y)}:
                        screen_x, screen_y = last_bbox.to_screen_coordinates(x, y)
                        logger.info(f"Mouse right click at {x},{y} ({screen_x},{screen_y})")
                        cxt = cxt.add_tool_result(
                            new_AnthropicToolResult(_id).add_text(f"Mouse right clicked at {x},{y}"))
                        pyautogui.rightClick(screen_x, screen_y)
                    case {'action': 'type', 'text': text}:
                        logger.info(f"Typing: {text}")
                        pyautogui.typewrite(text)
                        cxt = cxt.add_tool_result(new_AnthropicToolResult(_id).add_text(f"Typed: {text}"))
                    case {'action': 'screenshot'}:
                        tool_result, last_bbox = await a_chrome_screenshot(_id)
                        cxt = cxt.set_display_size(last_bbox.width, last_bbox.height)
                        logger.info(f'Took screenshot: {last_bbox}')
                        tool_result.add_text(f"Screenshot taken")
                        cxt = cxt.add_tool_result(tool_result)
                    case {'action': 'key', 'text': key_combination} | {'text': key_combination}:
                        logger.info(f"Keyboard input: {key_combination}")
                        await a_send_hotkey(key_combination)
                        cxt = cxt.add_tool_result(
                            new_AnthropicToolResult(_id).add_text(f"Keyboard input: {key_combination}"))
                    case _:
                        raise ValueError(f"Unknown tool use input: {_input}")
                on_cxt_update(cxt)
            case _:
                raise ValueError(f"Unknown content block: {cnt}")

    while True:
        if last_bbox is None:
            cxt, last_bbox = await a_add_chrome_screenshot_cxt(cxt)
            on_cxt_update(cxt)
        try:
            resp: BetaMessage = await cxt.acall()
        except Exception as e:
            if 'This action is restricted' in str(e):
                raise AnthropicAutomationDown(f"Anthropic seems to be down: {cxt.truncate_image_data()}") from e
            raise AnthropicAutomationException(f"Error in calling Anthropic: {cxt.truncate_image_data()}") from e
        usage: BetaUsage = resp.usage
        cost_usd = usage.input_tokens * 3 / 1000000 + usage.output_tokens * 15 / 1000000
        cum_price_usd += cost_usd
        logger.info(f"Response: {pformat(resp)}")
        block_n = len(resp.content)
        for block_i, cnt in enumerate(resp.content):
            try:
                await handle_block(cnt)
            except Exception as e:
                raise AnthropicAutomationException(
                    f"Error in handling block({block_i}): {cnt} in {cxt.truncate_image_data()}") from e
        if resp.stop_reason == 'tool_use':
            pass
        elif wait_user_input:
            cxt = cxt.add_message("user", input("User: "))
            on_cxt_update(cxt)
        else:
            return cxt


@injected
async def a_send_hotkey__pyautogui(key):
    key = key.lower()
    key = key.replace('return', 'enter')
    key = key.replace('meta', 'command')
    keys = key.split('+')

    if 'command' in keys:
        with pyautogui.hold('command'):
            await asyncio.sleep(0.1)
            pyautogui.press(*keys[1:])
    else:
        pyautogui.press(*keys)


test_cmd_k: IProxy = a_send_hotkey__pyautogui('command+k')
test_cmd_1: IProxy = a_send_hotkey__pyautogui('command+1')


@instance
async def test_open_browser_and_cmd_l(
        bring_chrome_to_front,
        a_send_hotkey,
        logger,
):
    logger.info("Bringing Chrome to front")
    bring_chrome_to_front()
    # pyautogui.click(300,300)
    logger.info("Sending command+l to Chrome")
    await asyncio.sleep(1)
    await a_send_hotkey('command+l')
    await asyncio.sleep(1)
    logger.info(f"Sending address to Chrome")
    pyautogui.typewrite('https://platform.openai.com/settings/organization/billing/history')
    pyautogui.press('enter')


SystemInstruction = """
Use Google Chrome for browsing web.
Use command+l to enter the address directly.
The pages are already logged in so you don't need to login.
When log in is needed, ask user to do that on that page opened, and then continue.
"""

test_check_gmail: IProxy = a_handle_action_loop(
    initial_msg=f"""
    {SystemInstruction}
    Navigate to gmail page, check if any important email is there.
    """
)

test_handle_action_loop: IProxy = a_handle_action_loop(
    initial_msg=f"""
    I need to gather invoices for the previous month for all teams I belong in OpenAI team(organization).
    
    Navigate to openai api billing page. When you think you are done, make sure to take a screenshot to see if it's done correctly.
    Use command+l to enter the following address directly.
    https://platform.openai.com/settings/organization/billing/history
    
    First, I need to switch a team. see the left top corner and click the team's name. It will open a dropdown menu to select a team.
    So click the team name from dropdown menu to switch to that team.
    
    I need to iterate through all teams to complete this task.
    Beware that the dropdown menu closes when you click anywhere else. So you have to click the team name every time to open the dropdown menu before switching to another team.
    
    Now, proceed to the next step.
    
    Press the 'View' button for each invoice to see the details.
    Pressing View button will open a new tab and we have to download '領収書' for each invoice by pressing "領収書をダウンロード" button, which has white text on black background.
    Beware that "請求書" is not the one we want.
    After pressing the "領収書をダウンロード" button, wait for 5 seconds before closing the tab with command+w to go back.
    Do not ever ask for continuing to the next step. You must continue.
    Repeat this process until you get all the invoice for the last month, for this team.
    Today is {datetime.now().strftime('%Y-%m-%d')}. Skip all billings that are older than the last month.
    
    Finally, repeat this process for all teams.
    (Skip 'AILab' and 'Cyberagent Kento Masui' team)
    
    Everytime you download the 領収書、add a line to downloads.csv at current directory with the following format:
    team_name, invoice id, amount, create date
   
    Current Directory: {os.getcwd()} 
    
    When taking screen shot is not needed, try to bunch up the commands and send them all at once.
    For example, you can send 'mouse move' 'mouse click 'keyboard input' all at once.
    This way we can process the commands faster.
    For adding lines, use bash command like `echo "team_name, invoice id, amount, create date" >> downloads.csv`
    
    """
)

test_handle_action_loop_programming: IProxy = a_handle_action_loop(
    initial_msg=f"""
    I need to gather invoices for the previous month for all teams I belong in OpenAI team(organization).
    
    Your job is to make a flow chart for the following task. Visit the actual page and see how we can automate the process.
    
    === TASK ===
    
    Navigate to openai api billing page. When you think you are done, make sure to take a screenshot to see if it's done correctly.
    Use command+l to enter the following address directly.
    https://platform.openai.com/settings/organization/billing/history
    
    First, I need to switch a team. see the left top corner and click the team's name. It will open a dropdown menu to select a team.
    So click the team name from dropdown menu to switch to that team.
    
    I need to iterate through all teams to complete this task.
    Beware that the dropdown menu closes when you click anywhere else. So you have to click the team name every time to open the dropdown menu before switching to another team.
    
    Now, proceed to the next step.
    
    Press the 'View' button for each invoice to see the details.
    Pressing View button will open a new tab and we have to download '領収書' for each invoice by pressing "領収書をダウンロード" button, which has white text on black background.
    Beware that "請求書" is not the one we want.
    After pressing the "領収書をダウンロード" button, wait for 5 seconds before closing the tab with command+w to go back.
    Do not ever ask for continuing to the next step. You must continue.
    Repeat this process until you get all the invoice for the last month, for this team.
    Today is {datetime.now().strftime('%Y-%m-%d')}.
    
    Finally, repeat this process for all teams.
    
    Everytime you download the 領収書、add a line to downloads.csv at current directory with the following format:
    team_name, invoice id, amount, create date
   
    Current Directory: {os.getcwd()} 
    
    For adding lines, use bash command like `echo "team_name, invoice id, amount, create date" >> downloads.csv`
    
    === TASK END ===
    """
)

list_twitter_following: IProxy = a_handle_action_loop(
    initial_msg="""
    Navigate to https://x.com/logistic_bot/following .
    Then, see my following list and list the following users to following.txt file.
    Use bash command like `echo "user_name" >> following.txt`, not str replace tool.
    You are at the current directory.
    
    You need to scroll down to see all the users.
    To scroll down, you must to press 'space' key.
    Append the users you see to following.txt file until no more users are shown.
    """
)

__design__=design(
    anthropic_client=anthropic_client,
    a_send_hotkey=a_send_hotkey__pyautogui,
)
