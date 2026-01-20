import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { DataBuilders } from '../../fixtures/data-builders'
import { ADMIN_USER } from '../../config/test-users'
import { createTempSkillZip } from '../../utils/skill-zip'
import * as fs from 'fs'

function buildSkillMd(description: string, body: string): string {
  return `---\ndescription: "${description}"\nversion: "0.1.0"\nauthor: "e2e"\ntags: ["e2e"]\n---\n\n${body}\n`
}

test.describe('Admin - Public Skills Management', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  let skillName = ''
  const tempDirs: string[] = []

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)

    await adminPage.navigateToTab('public-skills')
  })

  test.afterEach(async () => {
    // Cleanup skill if still exists
    if (skillName) {
      const listResponse = await apiClient.listPublicSkills(0, 200).catch(() => null)
      const items = (listResponse?.data as Array<{ id: number; name: string }> | null) || []
      const match = items.find(s => s.name === skillName)
      if (match) {
        await apiClient.deletePublicSkill(match.id).catch(() => {})
      }
      skillName = ''
    }

    for (const dir of tempDirs) {
      fs.rmSync(dir, { recursive: true, force: true })
    }
    tempDirs.length = 0
  })

  test('should upload, view, update, and delete a public skill', async ({ page }) => {
    skillName = DataBuilders.uniqueName('e2e-skill')

    const v1Body = `Hello from ${skillName} v1`
    const v2Body = `Hello from ${skillName} v2`

    const v1Zip = createTempSkillZip({
      skillName,
      skillMdContent: buildSkillMd(`E2E skill ${skillName} v1`, v1Body),
    })
    tempDirs.push(v1Zip.tempDir)

    const v2Zip = createTempSkillZip({
      skillName,
      skillMdContent: buildSkillMd(`E2E skill ${skillName} v2`, v2Body),
    })
    tempDirs.push(v2Zip.tempDir)

    // Upload
    await page
      .locator('button:has-text("Upload Skill"), button:has-text("上传技能")')
      .first()
      .click()

    const uploadDialog = page.locator('[role="dialog"]').first()
    await uploadDialog.waitFor({ state: 'visible' })

    await uploadDialog.locator('input#skill-name').fill(skillName)
    await uploadDialog.locator('input#file-input').setInputFiles(v1Zip.zipPath)
    await uploadDialog
      .locator('button:has-text("Upload Skill"), button:has-text("上传技能")')
      .last()
      .click()

    await adminPage.waitForToast().catch(() => {})

    await expect(page.locator(`text="${skillName}"`).first()).toBeVisible({ timeout: 10000 })

    const card = page.locator(`div:has-text("${skillName}")`).first()

    // View content
    await card.locator('button[title*="View"], button[title*="查看"]').first().click()
    const contentDialog = page.locator('[role="dialog"]').first()
    await contentDialog.waitFor({ state: 'visible' })
    await expect(contentDialog.locator('pre').first()).toContainText(v1Body)
    await contentDialog
      .locator('button:has-text("Cancel"), button:has-text("取消")')
      .first()
      .click()

    // Download (assert the API request succeeds)
    const downloadResponsePromise = page.waitForResponse(
      resp =>
        resp.url().includes('/api/v1/kinds/skills/public/') &&
        resp.url().includes('/download') &&
        resp.status() === 200
    )
    await card.locator('button[title*="Download"], button[title*="下载"]').first().click()
    await downloadResponsePromise

    // Update ZIP
    await card.locator('button[title*="Update"], button[title*="更新"]').first().click()
    const updateDialog = page.locator('[role="dialog"]').first()
    await updateDialog.waitFor({ state: 'visible' })
    await updateDialog.locator('input#file-input').setInputFiles(v2Zip.zipPath)
    await updateDialog
      .locator('button:has-text("Update Skill"), button:has-text("更新技能")')
      .first()
      .click()
    await adminPage.waitForToast().catch(() => {})

    // Verify updated content
    const updatedCard = page.locator(`div:has-text("${skillName}")`).first()
    await updatedCard.locator('button[title*="View"], button[title*="查看"]').first().click()
    const updatedContentDialog = page.locator('[role="dialog"]').first()
    await updatedContentDialog.waitFor({ state: 'visible' })
    await expect(updatedContentDialog.locator('pre').first()).toContainText(v2Body)
    await updatedContentDialog
      .locator('button:has-text("Cancel"), button:has-text("取消")')
      .first()
      .click()

    // Delete
    await updatedCard.locator('button[title*="Delete"], button[title*="删除"]').first().click()
    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })
    await page
      .locator(
        '[role="alertdialog"] button:has-text("Delete"), [role="alertdialog"] button:has-text("删除")'
      )
      .first()
      .click()
    await adminPage.waitForToast().catch(() => {})

    await expect(page.locator(`text="${skillName}"`).first()).toBeHidden({ timeout: 10000 })
    skillName = ''
  })
})
