import { useState } from 'react';
import { setupMfa, confirmMfa, disableMfa, type MfaSetupResponse } from '../api/mfa';

interface Props {
  mfaEnabled: boolean;
  onStatusChange: () => void;
}

export default function MfaSetup({ mfaEnabled, onStatusChange }: Props) {
  const [setupData, setSetupData] = useState<MfaSetupResponse | null>(null);
  const [code, setCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [showDisable, setShowDisable] = useState(false);

  async function handleStartSetup() {
    setLoading(true);
    setMessage(null);
    try {
      const data = await setupMfa();
      setSetupData(data);
    } catch (err: unknown) {
      setMessage((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Setup failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    setLoading(true);
    setMessage(null);
    try {
      await confirmMfa(code);
      setMessage('MFA enabled successfully!');
      setSetupData(null);
      setCode('');
      onStatusChange();
    } catch (err: unknown) {
      setMessage((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Verification failed');
    } finally {
      setLoading(false);
    }
  }

  async function handleDisable() {
    setLoading(true);
    setMessage(null);
    try {
      await disableMfa(disableCode);
      setMessage('MFA disabled');
      setDisableCode('');
      setShowDisable(false);
      onStatusChange();
    } catch (err: unknown) {
      setMessage((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to disable MFA');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">
          Multi-Factor Authentication
        </h3>
        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
          mfaEnabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {mfaEnabled ? 'Enabled' : 'Disabled'}
        </span>
      </div>

      {message && (
        <div className={`p-2 rounded text-sm ${message.includes('success') || message === 'MFA disabled' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message}
        </div>
      )}

      {!mfaEnabled && !setupData && (
        <button
          onClick={handleStartSetup}
          disabled={loading}
          className="px-4 py-2 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Setting up...' : 'Enable MFA (TOTP)'}
        </button>
      )}

      {setupData && (
        <div className="space-y-4 p-4 border border-gray-200 rounded-lg">
          <p className="text-sm text-gray-600">
            Scan the QR code with your authenticator app (Google Authenticator, Authy, etc.)
          </p>
          <div className="flex justify-center">
            <img
              src={`data:image/svg+xml;base64,${setupData.qr_code_svg}`}
              alt="TOTP QR Code"
              className="w-48 h-48"
            />
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1">Or enter this secret manually:</p>
            <code className="text-xs bg-gray-100 px-2 py-1 rounded select-all">{setupData.secret}</code>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Enter the 6-digit code from your app
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-center font-mono text-lg tracking-widest"
                placeholder="000000"
              />
              <button
                onClick={handleConfirm}
                disabled={loading || code.length !== 6}
                className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors text-sm"
              >
                {loading ? '...' : 'Verify'}
              </button>
            </div>
          </div>
          <button
            onClick={() => { setSetupData(null); setCode(''); }}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      )}

      {mfaEnabled && !showDisable && (
        <button
          onClick={() => setShowDisable(true)}
          className="px-4 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
        >
          Disable MFA
        </button>
      )}

      {showDisable && (
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Enter current TOTP code to disable
            </label>
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-center font-mono text-lg tracking-widest"
              placeholder="000000"
            />
          </div>
          <button
            onClick={handleDisable}
            disabled={loading || disableCode.length !== 6}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors text-sm"
          >
            Confirm
          </button>
          <button
            onClick={() => { setShowDisable(false); setDisableCode(''); }}
            className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
