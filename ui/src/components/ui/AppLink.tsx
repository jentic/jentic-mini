import { Link, type LinkProps } from 'react-router-dom';

type AppLinkProps = Omit<React.AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> &
	Omit<LinkProps, 'to'> & {
		href: string;
		external?: boolean;
	};

const EXTERNAL_RE = /^([a-z][a-z0-9+.-]*:|\/\/)/i;

function isExternalHref(href: string): boolean {
	return EXTERNAL_RE.test(href);
}

export function AppLink({ href, external, children, ...props }: AppLinkProps) {
	if (external || isExternalHref(href)) {
		return (
			<a
				href={href}
				target={props.target ?? '_blank'}
				rel={props.rel ?? 'noopener noreferrer'}
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
