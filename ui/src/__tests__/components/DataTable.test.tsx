import { render, screen, fireEvent } from '@testing-library/react';
import { DataTable, Column } from '@/components/ui/DataTable';

interface User {
	id: string;
	name: string;
	email: string;
}

const columns: Column<User>[] = [
	{ key: 'name', header: 'Name' },
	{ key: 'email', header: 'Email' },
];

const sampleData: User[] = [
	{ id: '1', name: 'Alice', email: 'alice@example.com' },
	{ id: '2', name: 'Bob', email: 'bob@example.com' },
];

describe('DataTable', () => {
	it('renders column headers', () => {
		render(<DataTable columns={columns} data={sampleData} getRowKey={(r) => r.id} />);

		expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument();
		expect(screen.getByRole('columnheader', { name: 'Email' })).toBeInTheDocument();
	});

	it('renders data rows with correct content', () => {
		render(<DataTable columns={columns} data={sampleData} getRowKey={(r) => r.id} />);

		expect(screen.getByRole('cell', { name: 'Alice' })).toBeInTheDocument();
		expect(screen.getByRole('cell', { name: 'bob@example.com' })).toBeInTheDocument();
	});

	it('shows empty message when data is empty', () => {
		render(
			<DataTable
				columns={columns}
				data={[]}
				getRowKey={(r) => r.id}
				emptyMessage="No users found."
			/>,
		);

		expect(screen.getByText('No users found.')).toBeInTheDocument();
		expect(screen.queryByRole('table')).not.toBeInTheDocument();
	});

	it('shows loading state when isLoading', () => {
		render(<DataTable columns={columns} data={[]} getRowKey={(r) => r.id} isLoading={true} />);

		expect(screen.getByText('Loading...')).toBeInTheDocument();
		expect(screen.queryByRole('table')).not.toBeInTheDocument();
	});

	it('calls onRowClick when row is clicked', () => {
		const onRowClick = vi.fn();
		render(
			<DataTable
				columns={columns}
				data={sampleData}
				getRowKey={(r) => r.id}
				onRowClick={onRowClick}
			/>,
		);

		fireEvent.click(screen.getByRole('cell', { name: 'Alice' }));
		expect(onRowClick).toHaveBeenCalledWith(sampleData[0]);
	});

	it('uses custom render function for columns', () => {
		const columnsWithRender: Column<User>[] = [
			{
				key: 'name',
				header: 'Name',
				render: (row) => <strong>{row.name.toUpperCase()}</strong>,
			},
			{ key: 'email', header: 'Email' },
		];

		render(<DataTable columns={columnsWithRender} data={sampleData} getRowKey={(r) => r.id} />);

		expect(screen.getByText('ALICE')).toBeInTheDocument();
		expect(screen.getByText('BOB')).toBeInTheDocument();
	});
});
