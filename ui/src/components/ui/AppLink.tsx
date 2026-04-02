import React from 'react';
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

export const AppLink = React.forwardRef<HTMLAnchorElement, AppLinkProps>(
	({ href, external, children, ...props }, ref) => {
		if (external || isExternalHref(href)) {
			return (
				<a
					ref={ref}
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
			<Link ref={ref} to={href} {...props}>
				{children}
			</Link>
		);
	},
);

AppLink.displayName = 'AppLink';
