import { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  type SubjectType,
  type AuthResponse,
  type MfaRequiredResponse,
  loginPassword,
  requestOtp,
  verifyOtp,
  getPasskeyLoginOptions,
  verifyPasskeyLogin,
} from '../api/auth';
import SubjectTypePicker from '../components/SubjectTypePicker';
import LoginForm from '../components/LoginForm';
import OtpForm from '../components/OtpForm';
import PasskeyLoginForm from '../components/PasskeyLoginForm';

type AuthMethod = 'password' | 'otp' | 'passkey';

const TABS: { value: AuthMethod; label: string }[] = [
  { value: 'password', label: 'Password' },
  { value: 'otp', label: 'OTP' },
  { value: 'passkey', label: 'Passkey' },
];

export default function LoginPage() {
  const [subjectType, setSubjectType] = useState<SubjectType | null>(null);
  const [method, setMethod] = useState<AuthMethod>('password');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleAuthSuccess(data: AuthResponse | MfaRequiredResponse) {
    // Check if MFA is required
    if ('mfa_required' in data) {
      window.location.href = `/mfa-challenge?token=${data.mfa_token}`;
      return;
    }
    const authData = data;
    localStorage.setItem('access_token', authData.access_token);
    localStorage.setItem('refresh_token', authData.refresh_token);
    window.location.href = '/dashboard';
  }

  function extractError(err: unknown): string {
    return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Authentication failed';
  }

  async function handlePasswordLogin(email: string, password: string) {
    if (!subjectType) return;
    setLoading(true);
    setError(null);
    try {
      const data = await loginPassword(subjectType, email, password);
      handleAuthSuccess(data);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpRequest(email: string) {
    if (!subjectType) return;
    setLoading(true);
    setError(null);
    try {
      await requestOtp(subjectType, email);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleOtpVerify(email: string, code: string) {
    if (!subjectType) return;
    setLoading(true);
    setError(null);
    try {
      const data = await verifyOtp(subjectType, email, code);
      handleAuthSuccess(data);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  async function handlePasskeyLogin(email: string) {
    if (!subjectType) return;
    setLoading(true);
    setError(null);
    try {
      const options = await getPasskeyLoginOptions(subjectType, email);
      const assertion = await navigator.credentials.get({ publicKey: options });
      if (!assertion) throw new Error('Passkey authentication cancelled');
      const data = await verifyPasskeyLogin(subjectType, email, assertion as PublicKeyCredential);
      handleAuthSuccess(data);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <h1 className="text-2xl font-bold text-gray-900 text-center mb-2">Sign In</h1>
          <p className="text-gray-500 text-center text-sm mb-6">Select your role and sign in</p>

          <div className="space-y-6">
            <SubjectTypePicker selected={subjectType} onSelect={(t) => { setSubjectType(t); setError(null); }} />

            {subjectType && (
              <>
                {/* Auth method tabs */}
                <div className="flex border-b border-gray-200">
                  {TABS.map((tab) => (
                    <button
                      key={tab.value}
                      onClick={() => { setMethod(tab.value); setError(null); }}
                      className={`flex-1 py-2 text-sm font-medium border-b-2 transition-colors ${
                        method === tab.value
                          ? 'border-gray-900 text-gray-900'
                          : 'border-transparent text-gray-400 hover:text-gray-600'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                {method === 'password' && (
                  <LoginForm onSubmit={handlePasswordLogin} isLoading={loading} error={error} />
                )}
                {method === 'otp' && (
                  <OtpForm
                    onRequestOtp={handleOtpRequest}
                    onVerifyOtp={handleOtpVerify}
                    isLoading={loading}
                    error={error}
                  />
                )}
                {method === 'passkey' && (
                  <PasskeyLoginForm onLogin={handlePasskeyLogin} isLoading={loading} error={error} />
                )}
              </>
            )}
          </div>

          <p className="mt-6 text-center text-sm text-gray-500">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-blue-600 hover:underline">Register</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
