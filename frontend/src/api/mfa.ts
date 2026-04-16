import client from './client';
import type { AuthResponse } from './auth';

export interface MfaSetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code_svg: string;
}

export async function setupMfa(): Promise<MfaSetupResponse> {
  const { data } = await client.post<MfaSetupResponse>('/mfa/setup');
  return data;
}

export async function confirmMfa(code: string): Promise<{ status: string; message: string }> {
  const { data } = await client.post('/mfa/confirm', { code });
  return data;
}

export async function disableMfa(code: string): Promise<{ status: string; message: string }> {
  const { data } = await client.post('/mfa/disable', { code });
  return data;
}

export async function verifyMfaChallenge(
  mfaToken: string,
  code: string,
): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>('/mfa/verify', {
    mfa_token: mfaToken,
    code,
  });
  return data;
}
