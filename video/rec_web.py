"""Records the web app: a text forward on the desktop layout, then an image forward on the phone layout.
Both are live checks (the server on 8011 starts with an empty cache).

usage: rec_web.py [desktop] [phone]
"""
import asyncio
import sys

from playwright.async_api import async_playwright

from common import BUILD, WEB
from rec import Recorder

NOTE = ("URGENT!! RBI has withdrawn the 2000 rupee note. You can exchange your 2000 rupee notes at any bank branch "
        "till 30 September, so hurry up. After that the notes will not be legal tender and will become worthless paper.")
LATEST = ".msg.in:last-child"


async def wait_for_answer(page, rec: Recorder) -> bool:
    await page.wait_for_selector(f"{LATEST} .p-claim", timeout=120_000)
    rec.mark("claims")
    await page.wait_for_selector(f"{LATEST} .result, {LATEST} .error-card", timeout=420_000)
    rec.mark("result")
    if await page.locator(f"{LATEST} .error-card").count():
        print("  !! error card:", await page.locator(f"{LATEST} .error-card").inner_text())
        return False
    print("  verdict:", await page.locator(f"{LATEST} .verdict-label").inner_text(), flush=True)
    return True


async def desktop(browser) -> None:
    print("desktop: text forward")
    width, height, scale = 1280, 760, 2
    context = await browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale, locale="en-IN")
    page = await context.new_page()
    await page.goto(WEB)
    await page.wait_for_selector(".welcome")
    await page.wait_for_timeout(800)
    rec = Recorder(page, BUILD / "rec" / "desktop", width, height, scale)
    await rec.start()
    await rec.hold(1.2)
    await rec.click(page.locator("#input"))
    await page.fill("#input", NOTE)
    rec.mark("pasted")
    await rec.hold(0.9)
    await rec.click(page.locator("#send"))
    rec.mark("sent")
    if await wait_for_answer(page, rec):
        await rec.hold(2.5)
        # Bring the verdict band to the top of the thread, then walk down the card.
        top = await page.evaluate(f"() => {{ const t = document.querySelector('#thread'); const r = document.querySelector('{LATEST} .result'); return t.scrollTop + r.getBoundingClientRect().top - t.getBoundingClientRect().top - 14; }}")
        await rec.scroll("#thread", top, 0.8)
        rec.mark("card_top")
        await rec.hold(2.0)
        claims = page.locator(f"{LATEST} details.claim")
        count = await claims.count()
        print("  claim rows:", count, [await claims.nth(i).locator(".chip").inner_text() for i in range(count)])
        # Open the outdated claim if there is one (it has the timeline), else the first.
        pick = 0
        for i in range(count):
            if "v-old" in (await claims.nth(i).get_attribute("class")):
                pick = i
        row = claims.nth(pick)
        offset = await page.evaluate(f"i => {{ const t = document.querySelector('#thread'); const r = document.querySelectorAll('{LATEST} details.claim')[i]; return t.scrollTop + r.getBoundingClientRect().top - t.getBoundingClientRect().top - 90; }}", pick)
        await rec.scroll("#thread", offset, 0.9)
        rec.mark("claims_list")
        await rec.hold(0.6)
        await rec.click(row.locator("summary"))
        rec.mark("claim_open")
        await rec.hold(2.2)
        await rec.scroll("#thread", offset + 330, 1.1)
        rec.mark("evidence")
        await rec.hold(2.5)
        await rec.scroll("#thread", offset + 700, 1.2)
        rec.mark("evidence_2")
        await rec.hold(2.0)
    await rec.stop()
    await context.close()


async def phone(browser) -> None:
    print("phone: image forward")
    width, height, scale = 400, 860, 2.5
    context = await browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale, locale="en-IN",
                                        has_touch=True, is_mobile=True)
    page = await context.new_page()
    await page.goto(WEB)
    await page.wait_for_selector(".welcome")
    await page.wait_for_timeout(800)
    rec = Recorder(page, BUILD / "rec" / "phone", width, height, scale)
    await rec.start()
    await rec.hold(1.0)
    await rec.click(page.locator("#attach"), kind="tap")
    await page.set_input_files("#file", str(BUILD / "inputs" / "laptop-forward.jpg"))
    await page.wait_for_selector("#attachment:not([hidden])")
    rec.mark("attached")
    await rec.hold(1.0)
    await rec.click(page.locator("#send"), kind="tap")
    rec.mark("sent")
    if await wait_for_answer(page, rec):
        await rec.hold(2.0)
        top = await page.evaluate(f"() => {{ const t = document.querySelector('#thread'); const r = document.querySelector('{LATEST} .result'); return t.scrollTop + r.getBoundingClientRect().top - t.getBoundingClientRect().top - 10; }}")
        await rec.scroll("#thread", top, 0.8)
        rec.mark("card_top")
        await rec.hold(2.0)
        await rec.scroll("#thread", top + 520, 1.2)
        rec.mark("card_mid")
        await rec.hold(2.0)
        await rec.scroll("#thread", top + 1040, 1.2)
        rec.mark("card_low")
        await rec.hold(2.0)
    await rec.stop()
    await context.close()


async def main() -> None:
    which = sys.argv[1:] or ["desktop", "phone"]
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        if "desktop" in which:
            await desktop(browser)
        if "phone" in which:
            await phone(browser)
        await browser.close()


asyncio.run(main())
