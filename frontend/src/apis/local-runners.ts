// SPDX-FileCopyrightText: 2025 Weibo, Inc.
//
// SPDX-License-Identifier: Apache-2.0

import apiClient from './client';
import type { LocalRunnerListResponse } from '@/types/api';

export const localRunnersApis = {
  async list(): Promise<LocalRunnerListResponse> {
    return apiClient.get('/local-runners');
  },
};
