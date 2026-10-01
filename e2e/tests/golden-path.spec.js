const { test, expect } = require("@playwright/test");
const path = require("path");

const TEST_XRAY = path.join(__dirname, "..", "..", "real_test", "new_xray_01.jpg.jpeg");

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 10000)}@example.com`;
}

test.describe("MediVision AI - golden path", () => {
  test("register -> patient -> upload X-ray -> AI result -> medical reports -> sign out", async ({
    page,
  }) => {
    const email = uniqueEmail();

    // ---------------------------------------------------------------
    // Register (redirected straight into an authenticated session)
    // ---------------------------------------------------------------
    await page.goto("/login");
    await page.getByText("Create an account").click();

    await page.getByPlaceholder("Dr. Jane Smith").fill("Dr E2E Test");
    await page.getByPlaceholder("Enter your email").fill(email);
    await page.getByPlaceholder("Enter your password").fill("e2e-test-password-123");
    await page.getByRole("button", { name: "Create Account" }).click();

    await expect(page).toHaveURL("/", { timeout: 20_000 });
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();

    // Real AI Model AUC card, sourced from GET /model/info - not a
    // hardcoded string. If the evaluation report is missing this still
    // renders "N/A", so the assertion just checks the card is present.
    await expect(page.getByText("AI Model AUC")).toBeVisible();

    // ---------------------------------------------------------------
    // Create a patient
    // ---------------------------------------------------------------
    await page.getByRole("link", { name: "Patients" }).click();
    await expect(page).toHaveURL("/patients");

    await page.getByRole("button", { name: "+ Add Patient" }).click();
    await page.getByPlaceholder("Enter full name").fill("E2E Test Patient");
    // The model is meant for young children; adults get an "unreliable" notice instead.
    await page.getByPlaceholder("Enter age").fill("4");
    await page.getByLabel("Gender").selectOption("Male");
    await page.getByPlaceholder("Enter phone number").fill("5559990000");
    await page.getByPlaceholder("Enter address").fill("1 Test Way");
    await page.getByRole("button", { name: "Add Patient", exact: true }).click();

    await expect(page.getByText("E2E Test Patient")).toBeVisible();

    // ---------------------------------------------------------------
    // Upload an X-ray and get a real AI prediction
    // ---------------------------------------------------------------
    await page.getByRole("link", { name: "X-Ray Analysis" }).click();
    await expect(page).toHaveURL("/xray");

    const patientSelect = page.locator("select.patient-select");
    const patientOptionLabel = await patientSelect
      .locator("option", { hasText: "E2E Test Patient" })
      .textContent();
    await patientSelect.selectOption({ label: patientOptionLabel });
    await page.locator('input[type="file"]').setInputFiles(TEST_XRAY);
    await page.getByRole("button", { name: "Analyze X-Ray" }).click();

    const resultPanel = page.locator(".ai-result-panel");
    // The first analysis after server start also loads the model lazily.
    await expect(resultPanel).toBeVisible({ timeout: 120_000 });
    // The sample X-ray is an adult film, which the image check correctly marks
    // "not reliable"; any clear verdict is acceptable for the happy path.
    await expect(resultPanel.locator(".ai-result-badge")).toHaveText(/Pneumonia|Normal|Not reliable/);
    await expect(resultPanel.getByText("Pneumonia probability", { exact: true })).toBeVisible();
    await expect(resultPanel.getByText("Operating threshold", { exact: true })).toBeVisible();
    await expect(
      resultPanel.getByText(/not a confirmed medical diagnosis/i)
    ).toBeVisible();

    // ---------------------------------------------------------------
    // The same report shows up in Medical Reports
    // ---------------------------------------------------------------
    await page.getByRole("link", { name: "Medical Reports" }).click();
    await expect(page).toHaveURL("/reports");

    await expect(page.getByText("new_xray_01.jpg.jpeg")).toBeVisible();
    await page.getByRole("button", { name: "View Report" }).first().click();

    await expect(page.locator(".report-xray-image")).toBeVisible();
    await expect(page.locator(".ai-result-panel")).toBeVisible();

    // ---------------------------------------------------------------
    // Sign out clears the session and protects routes again
    // ---------------------------------------------------------------
    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page).toHaveURL("/login");

    await page.goto("/patients");
    await expect(page).toHaveURL("/login");
  });

  test("AI Doctor answers an emergency message with the fixed urgent-care guidance", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/login");
    await page.getByText("Create an account").click();
    await page.getByPlaceholder("Dr. Jane Smith").fill("Dr Doctor Test");
    await page.getByPlaceholder("Enter your email").fill(email);
    await page.getByPlaceholder("Enter your password").fill("e2e-test-password-123");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page).toHaveURL("/", { timeout: 20_000 });

    await page.getByRole("link", { name: "Ask AI Doctor" }).click();
    await expect(page).toHaveURL("/ai-doctor");
    await expect(page.getByText(/not a diagnosis/i).first()).toBeVisible();

    // Emergency wording never goes to an AI model: the answer is fixed.
    await page.getByLabel("Your health question").fill("I have chest pain and my arm is numb");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText(/get urgent medical care now/i)).toBeVisible({ timeout: 30_000 });
  });

  test("unauthenticated visitors are redirected to /login", async ({ page }) => {
    await page.goto("/reports");
    await expect(page).toHaveURL("/login");
  });

  test("wrong password is rejected with an error, not a silent failure", async ({
    page,
  }) => {
    const email = uniqueEmail();

    await page.goto("/login");
    await page.getByText("Create an account").click();
    await page.getByPlaceholder("Dr. Jane Smith").fill("Dr Wrong Password");
    await page.getByPlaceholder("Enter your email").fill(email);
    await page.getByPlaceholder("Enter your password").fill("correct-password-1");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page).toHaveURL("/", { timeout: 20_000 });

    await page.getByRole("button", { name: "Sign Out" }).click();
    await expect(page).toHaveURL("/login");

    await page.getByPlaceholder("Enter your email").fill(email);
    await page.getByPlaceholder("Enter your password").fill("totally-wrong-password");
    await page.getByRole("button", { name: "Sign In" }).click();

    await expect(page.locator(".login-error")).toBeVisible();
    await expect(page).toHaveURL("/login");
  });
});
