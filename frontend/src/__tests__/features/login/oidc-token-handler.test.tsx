// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import { render, waitFor, act } from '@testing-library/react'
import { useRouter, useSearchParams } from 'next/navigation'
import { loginWithOidcToken } from '@/apis/user'
import OidcTokenHandler from '@/features/login/components/OidcTokenHandler'

const toastMock = jest.fn()

jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  useSearchParams: jest.fn(),
}))

jest.mock('@/apis/user', () => ({
  loginWithOidcToken: jest.fn(),
}))

jest.mock('@/hooks/useTranslation', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: toastMock,
  }),
}))

describe('OidcTokenHandler', () => {
  const routerReplaceMock = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
    ;(useRouter as jest.Mock).mockReturnValue({
      replace: routerReplaceMock,
    })
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it('stores token via loginWithOidcToken, cleans URL, and dispatches refresh event', async () => {
    // Arrange
    Object.defineProperty(window, 'location', {
      value: {
        href: 'http://localhost/settings?access_token=abc&token_type=bearer&login_success=true',
      },
      writable: true,
    })
    ;(useSearchParams as jest.Mock).mockReturnValue({
      get: (key: string) => {
        const map: Record<string, string> = {
          access_token: 'abc',
          token_type: 'bearer',
          login_success: 'true',
        }
        return map[key] ?? null
      },
    })
    ;(loginWithOidcToken as jest.Mock).mockResolvedValue(undefined)

    const refreshHandler = jest.fn()
    window.addEventListener('oidc-login-success', refreshHandler)

    // Act
    render(<OidcTokenHandler />)

    // Assert
    await waitFor(() => {
      expect(loginWithOidcToken).toHaveBeenCalledWith('abc')
      expect(routerReplaceMock).toHaveBeenCalledWith('/settings')
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'common:auth.login_success',
        })
      )
    })

    act(() => {
      jest.advanceTimersByTime(100)
    })

    expect(refreshHandler).toHaveBeenCalledTimes(1)
    window.removeEventListener('oidc-login-success', refreshHandler)
  })

  it('shows error toast and cleans URL when error is present', async () => {
    // Arrange
    Object.defineProperty(window, 'location', {
      value: {
        href: 'http://localhost/settings?error=access_denied&message=oops',
      },
      writable: true,
    })
    ;(useSearchParams as jest.Mock).mockReturnValue({
      get: (key: string) => {
        const map: Record<string, string> = {
          error: 'access_denied',
          message: 'oops',
        }
        return map[key] ?? null
      },
    })

    // Act
    render(<OidcTokenHandler />)

    // Assert
    await waitFor(() => {
      expect(toastMock).toHaveBeenCalledWith(
        expect.objectContaining({
          variant: 'destructive',
          title: 'common:auth.oidc_login_failed',
        })
      )
      expect(routerReplaceMock).toHaveBeenCalledWith('/settings')
    })
  })
})
