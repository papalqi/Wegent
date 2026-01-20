import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { DataBuilders } from '../../fixtures/data-builders'
import { ADMIN_USER } from '../../config/test-users'

type PublicModelJson = {
  spec?: {
    protocol?: string
    modelConfig?: {
      env?: {
        model?: string
        base_url?: string
      }
    }
  }
}

test.describe('Admin - Public Model Management', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  let testModelId: number | null = null

  const buildPublicModelJson = (modelName: string, displayName?: string) => ({
    apiVersion: 'agent.wecode.io/v1',
    kind: 'Model',
    metadata: {
      name: modelName,
      namespace: 'default',
      ...(displayName ? { displayName } : {}),
    },
    spec: {
      modelConfig: {
        env: {
          model: 'openai',
          model_id: 'gpt-4o-mini',
          api_key: 'test-key',
          base_url: 'https://api.openai.com/v1',
        },
      },
    },
    status: { state: 'Available' },
  })

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    // Login via API for API client operations
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)

    // Navigate directly to admin page (already authenticated via global setup storageState)
    await adminPage.navigateToTab('public-models')
  })

  test.afterEach(async () => {
    // Cleanup: delete test model if created
    if (testModelId) {
      await apiClient.adminDeletePublicModel(testModelId).catch(() => {})
      testModelId = null
    }
  })

  test('should access public model management page', async ({ page }) => {
    expect(adminPage.isOnAdminPage()).toBe(true)

    // Should see create button and header
    await expect(
      page.locator('button:has-text("Create Model"), button:has-text("创建模型")').first()
    ).toBeVisible({ timeout: 10000 })
  })

  test('should display public model list', async () => {
    const modelCount = await adminPage.getPublicModelCount()
    // May have 0 or more public models
    expect(modelCount).toBeGreaterThanOrEqual(0)
  })

  test('should open create public model dialog', async ({ page }) => {
    await adminPage.clickCreatePublicModel()

    await expect(page.locator('[role="dialog"]')).toBeVisible()
    await expect(page.locator('[role="dialog"] input#name')).toBeVisible()
    await expect(page.locator('[role="dialog"] input#modelId')).toBeVisible()
    await expect(page.locator('[role="dialog"] input#apiKey')).toBeVisible()
  })

  test('should create a new public model', async ({ page }) => {
    const modelName = DataBuilders.uniqueName('e2e-public-model')

    await adminPage.clickCreatePublicModel()

    await adminPage.fillPublicModelForm({
      name: modelName,
      namespace: 'default',
      providerType: 'openai',
      modelId: 'gpt-4o-mini',
      baseUrl: 'https://api.openai.com',
      apiKey: 'test-api-key',
    })
    await adminPage.submitPublicModelForm()

    await adminPage.waitForToast()

    // Verify via API and keep id for cleanup
    const modelsResponse = await apiClient.adminListPublicModels()
    const responseData = modelsResponse.data as {
      total: number
      items: Array<{ id: number; name: string }>
    }
    const created = (responseData.items || []).find(m => m.name === modelName)
    expect(created).toBeTruthy()
    testModelId = created?.id ?? null

    // Verify it also appears in UI list
    await page.reload()
    await adminPage.waitForPageLoad()
    expect(await adminPage.publicModelExists(modelName)).toBe(true)
  })

  test('should persist openai-responses protocol and normalize base url', async () => {
    const modelName = DataBuilders.uniqueName('e2e-public-model-responses')

    await adminPage.clickCreatePublicModel()

    await adminPage.fillPublicModelForm({
      name: modelName,
      providerType: 'openai-responses',
      modelId: 'gpt-4o-mini',
      baseUrl: 'https://api.openai.com',
      apiKey: 'test-api-key',
    })
    await adminPage.submitPublicModelForm()
    await adminPage.waitForToast()

    const modelsResponse = await apiClient.adminListPublicModels()
    const responseData = modelsResponse.data as {
      total: number
      items: Array<{ id: number; name: string; json: PublicModelJson }>
    }
    const created = (responseData.items || []).find(m => m.name === modelName)
    expect(created).toBeTruthy()
    testModelId = created?.id ?? null

    expect(created?.json?.spec?.protocol).toBe('openai-responses')
    expect(created?.json?.spec?.modelConfig?.env?.model).toBe('openai')
    expect(created?.json?.spec?.modelConfig?.env?.base_url).toBe('https://api.openai.com/v1')
  })

  test('should allow disabling auto /v1 suffix via # marker', async () => {
    const modelName = DataBuilders.uniqueName('e2e-public-model-baseurl-marker')

    await adminPage.clickCreatePublicModel()

    await adminPage.fillPublicModelForm({
      name: modelName,
      providerType: 'openai',
      modelId: 'gpt-4o-mini',
      baseUrl: 'https://api.openai.com#',
      apiKey: 'test-api-key',
    })
    await adminPage.submitPublicModelForm()
    await adminPage.waitForToast()

    const modelsResponse = await apiClient.adminListPublicModels()
    const responseData = modelsResponse.data as {
      total: number
      items: Array<{ id: number; name: string; json: PublicModelJson }>
    }
    const created = (responseData.items || []).find(m => m.name === modelName)
    expect(created).toBeTruthy()
    testModelId = created?.id ?? null

    expect(created?.json?.spec?.modelConfig?.env?.base_url).toBe('https://api.openai.com')
  })

  test('should show edit dialog for existing public model', async ({ page }) => {
    // Create a test model first via API
    const modelName = DataBuilders.uniqueName('e2e-edit-model')
    const createResponse = await apiClient.adminCreatePublicModel({
      name: modelName,
      json: buildPublicModelJson(modelName, 'E2E Edit Test Model'),
    })

    testModelId = (createResponse.data as { id: number }).id

    // Refresh page
    await page.reload()
    await adminPage.waitForPageLoad()

    await adminPage.clickEditPublicModel(modelName)
    await expect(page.locator('[role="dialog"]')).toBeVisible()
  })

  test('should delete a public model', async ({ page }) => {
    // Create a test model first via API
    const modelName = DataBuilders.uniqueName('e2e-delete-model')
    const createResponse = await apiClient.adminCreatePublicModel({
      name: modelName,
      json: buildPublicModelJson(modelName, 'E2E Delete Test Model'),
    })

    testModelId = (createResponse.data as { id: number }).id

    // Refresh page
    await page.reload()
    await adminPage.waitForPageLoad()

    await adminPage.clickDeletePublicModel(modelName)
    await adminPage.confirmDelete()
    await adminPage.waitForToast()

    // Verify model is gone
    await page.reload()
    await adminPage.waitForPageLoad()
    expect(await adminPage.publicModelExists(modelName)).toBe(false)
    testModelId = null
  })

  test('should validate JSON config when creating model', async ({ page }) => {
    await adminPage.clickCreatePublicModel()

    // Enable advanced JSON editor
    await page.locator('#advancedJsonSwitch').click()

    // Fill with invalid JSON
    await page.locator('textarea#advancedJson').fill('invalid json {')
    await adminPage.submitPublicModelForm()

    // Dialog should still be visible (validation failed)
    await expect(page.locator('[role="dialog"]')).toBeVisible()
  })
})
