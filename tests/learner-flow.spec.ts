import { expect, test } from '@playwright/test';

test('learner can discover a lesson, submit an answer, and see feedback', async ({ page }) => {
  await page.goto('/visual.html');

  await page.getByLabel('Topic to check').fill('Python functions');
  await page.getByRole('button', { name: 'Send topic' }).click();
  await page.getByRole('link', { name: /Return a value/ }).click();

  await expect(page.getByLabel('Coding workspace')).toBeVisible();
  await page.locator('.monaco-editor').click();
  await page.keyboard.insertText('def double(n):\n    return n * 2');
  await page.getByLabel('Explain your reasoning').fill('return sends the value back to the caller.');
  await page.getByRole('button', { name: 'Check my answer' }).click();

  await expect(page.getByRole('heading', { name: 'Your feedback' })).toBeVisible();
  await expect(page.getByText('A point to review')).toBeVisible();
  await expect(page.getByLabel('Coding workspace')).toHaveCount(0);
});
