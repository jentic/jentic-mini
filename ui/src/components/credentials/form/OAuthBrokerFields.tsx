import { useMutation, useQuery } from '@tanstack/react-query';
import { Loader2 } from 'lucide-react';
import { oauthBrokers } from '@/api/client';
import { AppLink } from '@/components/ui/AppLink';
import { Button } from '@/components/ui/Button';
import type { ApiOut } from '@/api/types';

/**
 * The OAuth-via-Pipedream sub-block. Three states:
 *
 *  1. Brokers query is in-flight — show a tiny spinner. We intentionally
 *     don't render the "no broker configured" path until we know,
 *     because it would flash for the legitimate case where a broker
 *     exists but the request is just slow.
 *  2. A broker exists — show "Create Connect Link" → on success
 *     swap to "Open Connect Link →" + a small "new link" reset action.
 *     The broker creates the upstream account when the user finishes
 *     the Pipedream-hosted flow; on return the credential row shows
 *     up in the workspace via the broker's webhook.
 *  3. No broker — show inline setup instructions linking to
 *     `/credentials` where the Pipedream broker can be configured.
 *
 * Owns the `connectLinkMutation` because it's specific to this UI;
 * extracting it would force callers to thread the mutation manually.
 *
 * `disabled` is set by the parent when the label field is empty —
 * the mutation needs a label so the resulting credential row is
 * identifiable in the list.
 */
export interface OAuthBrokerFieldsProps {
	selectedApi: ApiOut;
	label: string;
}

export function OAuthBrokerFields({ selectedApi, label }: OAuthBrokerFieldsProps) {
	const apiName = selectedApi.name ?? selectedApi.id;

	const { data: brokers, isLoading: brokersLoading } = useQuery({
		queryKey: ['oauth-brokers'],
		queryFn: () => oauthBrokers.list(),
		staleTime: 60 * 1000,
	});
	const activeBroker = brokers?.[0] ?? null;
	const hasOAuthBroker = !!activeBroker;

	const connectLinkMutation = useMutation({
		mutationFn: () => {
			if (!label.trim()) {
				throw new Error('Label is required for OAuth connections');
			}
			const parts = selectedApi.id.split('/');
			const appSlug = (selectedApi as any).app_slug ?? parts[parts.length - 1];
			return oauthBrokers.connectLink(activeBroker!.id, {
				app: appSlug,
				label: label.trim(),
				api_id: selectedApi.id,
			});
		},
	});

	if (brokersLoading) {
		return (
			<div className="text-muted-foreground flex items-center gap-2 text-xs">
				<Loader2 className="h-3 w-3 animate-spin" />
				Checking OAuth configuration…
			</div>
		);
	}

	if (hasOAuthBroker) {
		const connectUrl = connectLinkMutation.data?.connect_link_url;
		return (
			<div className="bg-muted/50 border-border space-y-3 rounded-lg border p-4">
				<p className="text-foreground text-sm font-medium">Connect via OAuth</p>
				<p className="text-muted-foreground text-xs">
					{apiName} uses OAuth 2.0. Generate a connect link to authorise access.
				</p>
				{connectLinkMutation.isError && (
					<p className="text-danger text-xs">
						Failed to generate connect link. Check your Pipedream broker config.
					</p>
				)}
				{!connectUrl ? (
					<Button
						variant="primary"
						size="sm"
						disabled={connectLinkMutation.isPending || !label.trim()}
						onClick={() => connectLinkMutation.mutate()}
					>
						{connectLinkMutation.isPending ? (
							<>
								<Loader2 className="mr-1 h-3 w-3 animate-spin" />
								Generating…
							</>
						) : (
							'Create Connect Link'
						)}
					</Button>
				) : (
					<div className="flex items-center gap-2">
						<Button
							variant="primary"
							size="sm"
							onClick={() => window.open(connectUrl, '_blank', 'noopener,noreferrer')}
						>
							Open Connect Link →
						</Button>
						<Button
							type="button"
							variant="ghost"
							size="sm"
							className="text-muted-foreground text-xs hover:underline"
							onClick={() => connectLinkMutation.reset()}
						>
							new link
						</Button>
					</div>
				)}
			</div>
		);
	}

	return (
		<div className="bg-muted/50 border-border space-y-3 rounded-lg border p-4">
			<p className="text-foreground text-sm font-medium">OAuth required</p>
			<p className="text-muted-foreground text-xs">
				{apiName} uses OAuth 2.0. Set up Pipedream Connect first:
			</p>
			<ol className="text-muted-foreground list-decimal space-y-1 pl-5 text-xs">
				<li>
					Go to <AppLink href="/credentials">Credentials</AppLink>
				</li>
				<li>
					Click <strong>Enable OAuth via Pipedream</strong> and enter your Pipedream
					client ID, secret, and project ID
				</li>
				<li>Return here to connect {apiName}</li>
			</ol>
		</div>
	);
}
