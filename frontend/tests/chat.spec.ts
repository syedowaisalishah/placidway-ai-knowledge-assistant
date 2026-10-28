import { test, expect } from "@playwright/test";

test("desktop welcomes visitors and displays real source-linked prices", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /A clearer way/ }),
  ).toBeVisible();
  await expect(
    page.getByText(/^(Source reading mode|Ready to help)$/),
  ).toBeVisible();
  await expect(page.locator(".brand-logo")).toHaveAttribute(
    "src",
    "/brand/placidway-logo.png",
  );
  expect(
    await page
      .locator(".brand-logo")
      .evaluate((img: HTMLImageElement) => img.naturalWidth),
  ).toBeGreaterThan(0);
  await page.screenshot({
    path: "../artifacts/screenshots/desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: /Find treatment costs/ }).click();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText(
    "$18,995",
  );
  await expect(page.locator(".assistant .answer-copy").last()).toContainText(
    "starting from",
  );
  await page.locator(".citation summary").first().click();
  await expect(
    page.getByRole("link", { name: "Read original page" }).first(),
  ).toHaveAttribute("href", /\/package\/7903\//);
  await page.screenshot({
    path: "../artifacts/screenshots/answer.png",
    fullPage: true,
  });
  await page.getByLabel("Your question").fill("And what about recovery time?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText(
    "program’s duration is not the same",
  );
  await page.getByRole("button", { name: /New conversation/ }).click();
  await expect(
    page.getByRole("heading", { name: /A clearer way/ }),
  ).toBeVisible();
  await expect(page.locator(".message")).toHaveCount(0);
});

test("source library and help dialog work", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Knowledge sources/ }).click();
  await expect(page.locator(".library-source")).toHaveCount(7);
  await expect(page.locator(".source-state.indexed")).toHaveCount(7);
  await page.getByRole("button", { name: "About this assistant" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("a simple greeting gets a welcome without an irrelevant quote link", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Your question").fill("HI");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText(
    "Hi! How can I help you today?",
  );
  await expect(page.locator(".assistant .answer-copy").last()).not.toContainText(
    "couldn’t verify",
  );
  await expect(page.locator(".assistant .quote-link")).toHaveCount(0);
  await expect(page.locator(".assistant .followup-suggestions button")).toHaveCount(
    4,
  );
  await page.screenshot({
    path: "../artifacts/screenshots/greeting-suggestions.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "What treatments does ITC offer?" })
    .click();
  await expect(page.locator(".assistant .citations").last()).toBeVisible({
    timeout: 30000,
  });
  await page.getByLabel("Your question").fill("Tell me a joke");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant").last()).toContainText(
    "I can help with the treatments",
  );
  await expect(page.locator(".assistant").last().locator(".quote-link")).toHaveCount(0);
  await expect(
    page.locator(".assistant").last().locator(".followup-suggestions button"),
  ).toHaveCount(4);
  await page.getByLabel("Your question").fill("How much does the package cost?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant").last()).toContainText(
    "Which treatment package do you mean",
  );
  await expect(
    page.locator(".assistant").last().locator(".followup-suggestions button"),
  ).toHaveCount(3);
});

test("acknowledgments and saved chats can be reopened and deleted", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Your question").fill("Hi");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText("How can I help you today?");
  await expect(page.getByRole("button", { name: "Delete conversation: Hi" })).toBeVisible();

  await page.getByRole("button", { name: /New conversation/ }).click();
  await page.getByLabel("Your question").fill("gret");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText("Thank you! How else can I help");
  await expect(page.locator(".history-item")).toHaveCount(2);

  await page.reload();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText("Thank you! How else can I help");
  await page.getByRole("button", { name: "Hi", exact: true }).click();
  await expect(page.locator(".assistant .answer-copy").last()).toContainText("How can I help you today?");
  await page.getByRole("button", { name: "Delete conversation: gret" }).click();
  await expect(page.locator(".history-item")).toHaveCount(1);
  await page.getByRole("button", { name: "Delete conversation: Hi" }).click();
  await expect(page.locator(".history-item")).toHaveCount(0);
  await page.reload();
  await expect(page.locator(".message")).toHaveCount(0);
});

test("mobile Arabic input and menu remain usable without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByLabel("Response language").selectOption("ar");
  await expect(page.getByLabel("Your question")).toHaveAttribute("dir", "rtl");
  await page
    .getByLabel("Your question")
    .fill("ما تكلفة علاج السرطان الغدي في المكسيك؟");
  await page.getByRole("button", { name: "إرسال الرسالة" }).click();
  await expect(page.locator(".assistant .message-body").last()).toHaveAttribute(
    "dir",
    "rtl",
  );
  await expect(page.locator(".assistant .answer-copy").last()).toContainText(
    "$18,995",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../artifacts/screenshots/mobile-arabic.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: /Knowledge sources/ }).click();
  await expect(
    page.getByRole("heading", { name: "See where answers come from." }),
  ).toBeVisible();
});

test("network failures produce an honest recoverable state", async ({
  page,
}) => {
  await page.route("**/api/chat", (route) => route.abort("failed"));
  await page.goto("/");
  await page
    .getByLabel("Your question")
    .fill("What treatments does ITC offer?");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.locator(".error-message")).toBeVisible();
  await expect(page.getByLabel("Your question")).toBeEnabled();
  await page.getByLabel("Your question").fill("Try again");
  await expect(
    page.getByRole("button", { name: "Send message" }),
  ).toBeEnabled();
});
