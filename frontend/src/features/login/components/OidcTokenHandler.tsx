// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

'use client'

import { useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useTranslation } from '@/hooks/useTranslation'
import { useToast } from '@/hooks/use-toast'
import { loginWithOidcToken } from '@/apis/user'

/**
 * OIDC Token Handler Component
 *
 * Handles token parameters from OIDC callback redirects
 * When backend OIDC callback succeeds, it redirects to /login/oidc?access_token=xxx&token_type=bearer&login_success=true
 * This component is responsible for extracting these parameters and storing them in localStorage
 */
export default function OidcTokenHandler() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const router = useRouter()
  const searchParams = useSearchParams()

  useEffect(() => {
    const accessToken = searchParams.get('access_token')
    const error = searchParams.get('error')
    const loginSuccess = searchParams.get('login_success')
    const errorMessage = searchParams.get('message')

    if (error) {
      console.error('OIDC login failed:', error, errorMessage)
      toast({
        variant: 'destructive',
        title: t('common:auth.oidc_login_failed'),
        description: errorMessage || error,
      })

      const url = new URL(window.location.href)
      url.searchParams.delete('error')
      url.searchParams.delete('message')
      router.replace(url.pathname + url.search)
      return
    }

    if (loginSuccess === 'true' && accessToken) {
      loginWithOidcToken(accessToken)
        .then(() => {
          toast({
            title: t('common:auth.login_success'),
          })

          const url = new URL(window.location.href)
          url.searchParams.delete('access_token')
          url.searchParams.delete('token_type')
          url.searchParams.delete('login_success')

          router.replace(url.pathname + url.search)

          setTimeout(() => {
            console.log('Trigger user status refresh')
            window.dispatchEvent(new Event('oidc-login-success'))
          }, 100)
        })
        .catch(err => {
          console.error('OIDC token processing failed:', err)
          toast({
            variant: 'destructive',
            title: t('common:auth.oidc_login_failed'),
          })
        })
    }
  }, [router, searchParams, t, toast])

  return null
}
