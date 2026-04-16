import { useState, useRef, type FormEvent, type KeyboardEvent } from 'react';

interface Props {
  onRequestOtp: (email: string) => Promise<void>;
  onVerifyOtp: (email: string, code: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

export default function OtpForm({ onRequestOtp, onVerifyOtp, isLoading, error }: Props) {
  const [email, setEmail] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  async function handleRequestOtp(e: FormEvent) {
    e.preventDefault();
    await onRequestOtp(email);
    setOtpSent(true);
  }

  async function handleVerify(e: FormEvent) {
    e.preventDefault();
    const code = digits.join('');
    if (code.length === 6) {
      await onVerifyOtp(email, code);
    }
  }

  function handleDigitChange(index: number, value: string) {
    if (!/^\d?$/.test(value)) return;
    const next = [...digits];
    next[index] = value;
    setDigits(next);
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index: number, e: KeyboardEvent) {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  if (!otpSent) {
    return (
      <form onSubmit={handleRequestOtp} className="space-y-4">
        {error && <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="you@example.com"
          />
        </div>
        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2.5 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {isLoading ? 'Sending...' : 'Send OTP Code'}
        </button>
      </form>
    );
  }

  return (
    <form onSubmit={handleVerify} className="space-y-4">
      {error && <div className="p-3 rounded-lg bg-red-50 text-red-700 text-sm">{error}</div>}
      <p className="text-sm text-gray-600 text-center">
        OTP sent to <span className="font-medium">{email}</span>
        <br />
        <span className="text-xs text-gray-400">(Check backend console for the code)</span>
      </p>
      <div className="flex justify-center gap-2">
        {digits.map((d, i) => (
          <input
            key={i}
            ref={(el) => { inputRefs.current[i] = el; }}
            type="text"
            inputMode="numeric"
            maxLength={1}
            value={d}
            onChange={(e) => handleDigitChange(i, e.target.value)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            className="w-11 h-13 text-center text-xl font-mono border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        ))}
      </div>
      <button
        type="submit"
        disabled={isLoading || digits.join('').length < 6}
        className="w-full py-2.5 bg-gray-900 text-white rounded-lg font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
      >
        {isLoading ? 'Verifying...' : 'Verify & Sign In'}
      </button>
      <button
        type="button"
        onClick={() => { setOtpSent(false); setDigits(['', '', '', '', '', '']); }}
        className="w-full text-sm text-gray-500 hover:text-gray-700"
      >
        Use a different email
      </button>
    </form>
  );
}
