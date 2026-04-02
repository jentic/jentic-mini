import { useState } from 'react';
import { Copy, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface OneTimeKeyDisplayProps {
	keyValue: string;
	onConfirm: () => void;
	title?: string;
}

export function OneTimeKeyDisplay({ keyValue, onConfirm, title }: OneTimeKeyDisplayProps) {
	const [copied, setCopied] = useState(false);
	const [confirmed, setConfirmed] = useState(false);

	const handleCopy = async () => {
		await navigator.clipboard.writeText(keyValue);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	};

	return (
		<div className="border-danger/40 bg-danger/5 space-y-4 rounded-xl border-2 p-5">
			<div className="flex items-start gap-3">
				<AlertTriangle className="text-danger mt-0.5 h-5 w-5 shrink-0" />
				<div>
					<p className="text-danger font-semibold">{title ?? 'API Key Generated'}</p>
					<p className="text-muted-foreground mt-1 text-sm">
						This key will{' '}
						<strong className="text-foreground">never be shown again</strong>. Copy it
						now and store it securely before dismissing.
					</p>
				</div>
			</div>

			<div className="flex items-center gap-2">
				<code className="bg-background border-border text-foreground flex-1 rounded-lg border px-4 py-3 font-mono text-sm break-all">
					{keyValue}
				</code>
				<Button variant="secondary" size="sm" onClick={handleCopy} className="shrink-0">
					{copied ? (
						<>
							<CheckCircle className="text-success h-4 w-4" /> Copied
						</>
					) : (
						<>
							<Copy className="h-4 w-4" /> Copy
						</>
					)}
				</Button>
			</div>

			<label className="flex cursor-pointer items-center gap-3">
				{/* eslint-disable-next-line no-restricted-syntax -- No Checkbox primitive yet */}
				<input
					type="checkbox"
					checked={confirmed}
					onChange={(e) => setConfirmed(e.target.checked)}
					className="border-border h-4 w-4 rounded"
				/>
				<span className="text-foreground text-sm">
					I've copied this key to a safe place
				</span>
			</label>

			<Button onClick={onConfirm} disabled={!confirmed} className="w-full">
				Done — dismiss
			</Button>
		</div>
	);
}
