from playwright.async_api import Page


async def perform_login(page: Page, username: str, password: str) -> bool:
    """SSO 로그인 처리. 성공 시 True, 실패 시 False 반환."""
    try:
        login_button = await page.query_selector(".login_btn a")
        if login_button:
            await login_button.click()
            await page.wait_for_load_state("networkidle")

        await page.fill("input#userid", username)
        await page.fill("input#pwd", password)

        async with page.expect_navigation(wait_until="networkidle"):
            await page.click("a.btn_login")

        if "login" in page.url:
            return False

        await page.wait_for_load_state("networkidle")
        return True

    except Exception:
        return False


async def ensure_logged_in(page: Page, username: str, password: str) -> bool:
    """현재 페이지가 로그인 페이지이면 로그인을 수행."""
    if "login" not in page.url:
        return True
    return await perform_login(page, username, password)
