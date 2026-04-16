import client from './client';

export interface SubjectResponse {
  id: string;
  email: string;
  display_name: string;
  subject_type: string;
  mfa_enabled: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  subject: SubjectResponse;
}

export interface CredentialInfo {
  id: string;
  type: string;
  created_at: string | null;
  last_used_at: string | null;
}

export type SubjectType = 'member' | 'community-staff' | 'platform-staff';

export async function register(
  subjectType: SubjectType,
  email: string,
  password: string,
  displayName: string,
): Promise<SubjectResponse> {
  const { data } = await client.post<SubjectResponse>(
    `/auth/${subjectType}/register`,
    { email, password, display_name: displayName },
  );
  return data;
}

export interface MfaRequiredResponse {
  mfa_required: true;
  mfa_token: string;
}

export async function loginPassword(
  subjectType: SubjectType,
  email: string,
  password: string,
): Promise<AuthResponse | MfaRequiredResponse> {
  const { data } = await client.post<AuthResponse | MfaRequiredResponse>(
    `/auth/${subjectType}/login/password`,
    { email, password },
  );
  return data;
}

export async function requestOtp(
  subjectType: SubjectType,
  email: string,
): Promise<void> {
  await client.post(`/auth/${subjectType}/login/otp/request`, { email });
}

export async function verifyOtp(
  subjectType: SubjectType,
  email: string,
  otpCode: string,
): Promise<AuthResponse> {
  const { data } = await client.post<AuthResponse>(
    `/auth/${subjectType}/login/otp/verify`,
    { email, otp_code: otpCode },
  );
  return data;
}

export async function getPasskeyLoginOptions(
  subjectType: SubjectType,
  email: string,
): Promise<PublicKeyCredentialRequestOptions> {
  const { data } = await client.post(
    `/auth/${subjectType}/login/passkey/options`,
    { email },
  );
  // Convert base64url strings to ArrayBuffers for WebAuthn API
  return {
    ...data,
    challenge: base64urlToBuffer(data.challenge),
    allowCredentials: (data.allowCredentials || []).map((c: { id: string; type: string }) => ({
      ...c,
      id: base64urlToBuffer(c.id),
    })),
  } as PublicKeyCredentialRequestOptions;
}

export async function verifyPasskeyLogin(
  subjectType: SubjectType,
  email: string,
  credential: PublicKeyCredential,
): Promise<AuthResponse> {
  const response = credential.response as AuthenticatorAssertionResponse;
  const { data } = await client.post<AuthResponse>(
    `/auth/${subjectType}/login/passkey/verify`,
    {
      email,
      credential: {
        id: credential.id,
        rawId: bufferToBase64url(credential.rawId),
        type: credential.type,
        response: {
          authenticatorData: bufferToBase64url(response.authenticatorData),
          clientDataJSON: bufferToBase64url(response.clientDataJSON),
          signature: bufferToBase64url(response.signature),
          userHandle: response.userHandle ? bufferToBase64url(response.userHandle) : null,
        },
      },
    },
  );
  return data;
}

export async function getPasskeyRegisterOptions(): Promise<PublicKeyCredentialCreationOptions> {
  const { data } = await client.post('/credentials/passkey/register/options');
  return {
    ...data,
    challenge: base64urlToBuffer(data.challenge),
    user: {
      ...data.user,
      id: base64urlToBuffer(data.user.id),
    },
    excludeCredentials: (data.excludeCredentials || []).map((c: { id: string; type: string }) => ({
      ...c,
      id: base64urlToBuffer(c.id),
    })),
  } as PublicKeyCredentialCreationOptions;
}

export async function verifyPasskeyRegister(
  credential: PublicKeyCredential,
): Promise<{ status: string }> {
  const response = credential.response as AuthenticatorAttestationResponse;
  const { data } = await client.post('/credentials/passkey/register/verify', {
    id: credential.id,
    rawId: bufferToBase64url(credential.rawId),
    type: credential.type,
    response: {
      attestationObject: bufferToBase64url(response.attestationObject),
      clientDataJSON: bufferToBase64url(response.clientDataJSON),
    },
  });
  return data;
}

export async function listCredentials(): Promise<CredentialInfo[]> {
  const { data } = await client.get<CredentialInfo[]>('/credentials/');
  return data;
}

export async function deleteCredential(id: string): Promise<void> {
  await client.delete(`/credentials/${id}`);
}

export async function logout(): Promise<void> {
  await client.post('/auth/logout');
}

export async function getMe(): Promise<SubjectResponse> {
  const { data } = await client.get<SubjectResponse>('/auth/me');
  return data;
}

// --- WebAuthn helpers ---

function base64urlToBuffer(base64url: string): ArrayBuffer {
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
  const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4));
  const binary = atob(base64 + pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function bufferToBase64url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
