import uuid

import pytest
from playwright.sync_api import expect


@pytest.mark.parametrize("editor", ["prosemirror", "tiptap"])
def test_text_collaboration(playwright, editor):
    room_name = uuid.uuid4().hex
    room_url = f"http://localhost:8000/{editor}/{room_name}/"
    firefox = playwright.firefox
    browser_1 = firefox.launch()
    page_1 = browser_1.new_page()
    browser_2 = firefox.launch()
    page_2 = browser_2.new_page()
    page_1.goto(room_url)
    text_1 = page_1.locator(".ProseMirror")
    text_1.click()
    sample_text = "Hello World"
    page_1.keyboard.type(sample_text)
    page_2.goto(room_url)
    text_2 = page_2.locator(".ProseMirror")
    text_2.click()
    expect(text_2).to_contain_text(sample_text)
    text_2.press("Enter")
    sample_text_2 = "Goodbye"
    text_2.type(sample_text_2)
    expect(text_1).to_contain_text(sample_text_2)
    browser_1.close()
    browser_2.close()
