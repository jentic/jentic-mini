import { Component } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from './Button';

interface Props {
	children: ReactNode;
	fallback?: ReactNode;
	resetKey?: string;
}

interface State {
	error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
	state: State = { error: null };

	static getDerivedStateFromError(error: Error): State {
		return { error };
	}

	componentDidCatch(error: Error, info: ErrorInfo) {
		console.error('[ErrorBoundary]', error, info.componentStack);
	}

	componentDidUpdate(prevProps: Props) {
		if (prevProps.resetKey !== this.props.resetKey && this.state.error) {
			this.setState({ error: null });
		}
	}

	render() {
		if (this.state.error) {
			if (this.props.fallback) return this.props.fallback;

			return (
				<div className="border-border bg-muted rounded-xl border p-8 text-center">
					<AlertTriangle className="text-warning mx-auto mb-3 h-8 w-8" />
					<p className="text-foreground mb-1 text-sm font-medium">Something went wrong</p>
					<p className="text-muted-foreground mb-4 text-xs">{this.state.error.message}</p>
					<Button
						variant="secondary"
						size="sm"
						onClick={() => this.setState({ error: null })}
					>
						Try again
					</Button>
				</div>
			);
		}

		return this.props.children;
	}
}
