import { Link, type LinkProps } from 'react-router-dom';

type AppLinkProps = Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> &
	Omit<LinkProps, 'to'> & {
		href: string;
		external?: boolean;
	};

const EXTERNAL_RE = /^([a-z][a-z0-9+.-]*:|\/\/)/i;
const UNSAFE_RE = /^(javascript|data|vbscript):/i;

function isExternalHref(href: string): boolean {
	return EXTERNAL_RE.test(href);
}

export function AppLink({ href, external, target, rel, children, ...props }: AppLinkProps) {
	if (UNSAFE_RE.test(href)) {
		return (
			<span {...props} role="link" aria-disabled="true">
				{children}
			</span>
		);
	}

	if (external || isExternalHref(href)) {
		return (
			<a
				href={href}
				target={target ?? '_blank'}
				rel={rel ?? 'noopener noreferrer'}
				{...props}
			>
				{children}
			</a>
		);
	}

	return (
		<Link to={href} {...props}>
			{children}
		</Link>
	);
}
