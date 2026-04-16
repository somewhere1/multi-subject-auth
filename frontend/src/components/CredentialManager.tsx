import { useState, useEffect } from 'react';
import {
  listCredentials,
  deleteCredential,
  getPasskeyRegisterOptions,
  verifyPasskeyRegister,
  type CredentialInfo,
} from '../api/auth';

const TYPE_LABELS: Record<string, string> = {
  password: 'Password',
  otp: 'OTP',
  passkey: 'Passkey',
};

export default function CredentialManager() {
  const [credentials, setCredentials] = useState<CredentialInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [registering, setRegistering] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function fetchCredentials() {
    setLoading(true);
    try {
      const data = await listCredentials();
      setCredentials(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchCredentials(); }, []);

  async function handleRegisterPasskey() {
    setRegistering(true);
    setMessage(null);
    try {
      const options = await getPasskeyRegisterOptions();
      const credential = await navigator.credentials.create({ publicKey: options });
      if (!credential) throw new Error('Passkey creation cancelled');
      await verifyPasskeyRegister(credential as PublicKeyCredential);
      setMessage('Passkey registered successfully!');
      await fetchCredentials();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to register passkey';
      setMessage(msg);
    } finally {
      setRegistering(false);
    }
  }

  async function handleDelete(id: string) {
    await deleteCredential(id);
    setCredentials((prev) => prev.filter((c) => c.id !== id));
  }

  if (loading) return <div className="text-gray-500 text-sm">Loading credentials...</div>;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Credentials</h3>
        <button
          onClick={handleRegisterPasskey}
          disabled={registering}
          className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {registering ? 'Registering...' : '+ Add Passkey'}
        </button>
      </div>

      {message && (
        <div className={`p-2 rounded text-sm ${message.includes('success') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message}
        </div>
      )}

      {credentials.length === 0 ? (
        <p className="text-gray-500 text-sm">No credentials registered</p>
      ) : (
        <div className="space-y-2">
          {credentials.map((cred) => (
            <div
              key={cred.id}
              className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
            >
              <div>
                <span className="font-medium text-gray-800 text-sm">
                  {TYPE_LABELS[cred.type] || cred.type}
                </span>
                <div className="text-xs text-gray-500 mt-0.5">
                  Created: {cred.created_at ? new Date(cred.created_at).toLocaleDateString() : 'N/A'}
                  {cred.last_used_at && ` · Last used: ${new Date(cred.last_used_at).toLocaleDateString()}`}
                </div>
              </div>
              {cred.type !== 'password' && (
                <button
                  onClick={() => handleDelete(cred.id)}
                  className="px-3 py-1 text-xs text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
                >
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
