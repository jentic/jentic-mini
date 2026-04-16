import { AlertTriangle, Copy, Check } from 'lucide-react';
import React, { useState } from 'react';
import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface ErrorAlertProps {
	/** Either a raw message string or an Error / ApiError instance */
	message: string | Error;
	className?: string;
}

/** Build a single copyable markdown string from the no_security_scheme error data. */
function buildNoSchemeMarkdown(data: Record<string, any>): string {
	const overlayEndpoint: string = data.submit_to ?? `POST /apis/${data.api_id}/overlays`;
	const examples: Record<string, any> = data.examples ?? {};

	const lines: string[] = [];

	lines.push(`## No security scheme for \`${data.api_id}\``);
	lines.push('');
	lines.push(data.message);
	lines.push('');
	lines.push('### Instructions');
	lines.push('');
	lines.push(data.instructions);
	lines.push('');
	lines.push(`Submit the overlay to: \`${overlayEndpoint}\``);
	if (data.note) {
		lines.push('');
		lines.push(`> **Note:** ${data.note}`);
	}

	const exampleKeys = Object.keys(examples);
	if (exampleKeys.length > 0) {
		lines.push('');
		lines.push('### Overlay examples');
		lines.push('');
		lines.push(
			'Pick the pattern that matches how this API authenticates, fill in the real header/parameter names, and POST it to the endpoint above.',
		);

		for (const key of exampleKeys) {
			const ex = { ...examples[key] };
			// Strip internal _note from JSON output but include it as prose
			const prose: string | undefined = ex._note;
			delete ex._note;

			const label = key.replaceAll('_', ' ');
			lines.push('');
			lines.push(`#### ${label}`);
			if (prose) {
				lines.push('');
				lines.push(prose);
			}
			lines.push('');
			lines.push('```json');
			lines.push(JSON.stringify(ex, null, 2));
			lines.push('```');
		}
	}

	return lines.join('\n');
}

/** Render a structured `no_security_scheme` API error as a single copyable block. */
function NoSchemeError({ data }: { data: Record<string, any> }) {
	const [copied, setCopied] = useState(false);
	const overlayEndpoint: string = data.submit_to ?? `POST /apis/${data.api_id}/overlays`;
	const examples: Record<string, any> = data.examples ?? {};
	const exampleKeys = Object.keys(examples);
	const markdown = buildNoSchemeMarkdown(data);

	const copy = () => {
		navigator.clipboard.writeText(markdown).then(() => {
			setCopied(true);
			setTimeout(() => setCopied(false), 2000);
		});
	};

	return (
		<div className="space-y-3 text-xs">
			{/* Header row */}
			<div className="flex items-start justify-between gap-2">
				<p className="text-sm leading-snug font-medium">{data.message}</p>
				<Button
					variant="outline"
					size="sm"
					type="button"
					onClick={copy}
					title="Copy everything as markdown"
					className={cn(
						'flex shrink-0 items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors',
						copied
							? 'border-success/40 bg-success/10 text-success'
							: 'border-border bg-background/60 text-muted-foreground hover:bg-muted hover:text-foreground',
					)}
				>
					{copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
					{copied ? 'Copied' : 'Copy as markdown'}
				</Button>
			</div>

			{/* Instructions */}
			<div className="bg-background/60 border-border/50 space-y-1.5 rounded-md border p-3">
				<p className="text-muted-foreground text-[10px] font-semibold tracking-wide uppercase">
					Instructions for your agent
				</p>
				<p className="leading-relaxed">{data.instructions}</p>
				<p className="text-muted-foreground">
					Submit to:{' '}
					<code className="bg-muted text-foreground rounded px-1 py-0.5 font-mono">
						{overlayEndpoint}
					</code>
				</p>
				{data.note && (
					<p className="text-muted-foreground border-border/40 mt-1.5 border-t pt-1.5 italic">
						{data.note}
					</p>
				)}
			</div>

			{/* Examples */}
			{exampleKeys.length > 0 && (
				<div className="space-y-2">
					<p className="text-muted-foreground text-[10px] font-semibold tracking-wide uppercase">
						Overlay examples — pick the right pattern, fill in header names, submit
					</p>
					{exampleKeys.map((key) => {
						const ex = { ...examples[key] };
						const prose: string | undefined = ex._note;
						delete ex._note;
						const label = key.replaceAll('_', ' ');
						return (
							<div
								key={key}
								className="border-border/40 bg-muted/30 overflow-hidden rounded-md border"
							>
								<div className="bg-muted/60 border-border/30 border-b px-3 py-1.5">
									<span className="text-foreground font-mono text-[11px] font-semibold">
										{label}
									</span>
									{prose && (
										<p className="text-muted-foreground mt-0.5 leading-relaxed">
											{prose}
										</p>
									)}
								</div>
								<pre className="overflow-x-auto p-3 text-[11px] leading-relaxed">
									{JSON.stringify(ex, null, 2)}
								</pre>
							</div>
						);
					})}
				</div>
			)}
		</div>
	);
}

export function ErrorAlert({ message, className }: ErrorAlertProps) {
	const isApiError = message instanceof ApiError;
	const apiData = isApiError ? (message as ApiError).data : null;
	const errorCode = apiData?.error as string | undefined;
	const text = typeof message === 'string' ? message : message.message;

	return (
		<div
			role="alert"
			className={cn(
				'bg-danger/10 border-danger/30 text-danger rounded-lg border px-4 py-3 text-sm',
				className,
			)}
		>
			<div className="flex items-start gap-3">
				<AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
				<div className="min-w-0 flex-1">
					{errorCode === 'no_security_scheme' && apiData ? (
						<NoSchemeError data={apiData} />
					) : (
						<span>{text}</span>
					)}
				</div>
			</div>
		</div>
	);
}
