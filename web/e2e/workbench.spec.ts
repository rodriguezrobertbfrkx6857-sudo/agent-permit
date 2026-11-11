import { test, expect } from "@playwright/test";
import { existsSync, unlinkSync } from "node:fs";
// Database isolated from the developer's interactive workbench.
// Each CI run starts in a clean checkout; remove only this named test database before launch via test script.
test("primary workflow and audit evidence", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  const capture = async () => {
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
    await page.setViewportSize({width:1440,height:1000});
    await page.evaluate(()=>window.scrollTo(0,0));
    if (process.env.UPDATE_SCREENSHOTS === "1")
      await page.screenshot({ path: "../docs/screenshot.png", fullPage: true });
  };
  await page.getByRole("button", { name: "检查并提交提案" }).click();
  await expect(page.getByText("PENDING", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "以 Reviewer 身份批准这组参数" })
    .click();
  await expect(page.getByText("APPROVED", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "使用能力令牌执行" }).click();
  await expect(page.getByText("EXECUTED", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "重试同一请求，验证幂等" }).click();
  await expect(
    page.getByText("幂等重放：返回原结果，未重复写入。"),
  ).toBeVisible();
  await capture();
  await page.getByRole("button", { name: "路径越权", exact: true }).click();
  await page.getByRole("button", { name: "检查并提交提案" }).click();
  await expect(page.getByText("DENIED", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "审计证据" }).click();
  await expect(page.getByText("VALID", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});
test("mobile layout remains within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(390);
  await expect(page.locator("h1")).toBeVisible();
});
