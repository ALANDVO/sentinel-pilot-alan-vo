// UI Component Tests
import { render, screen, fireEvent } from '@testing-library/react'
import { Button, Input, Card, Modal, Badge, LoadingSpinner, EmptyState, ErrorState } from './UI'

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('calls onClick handler', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('applies variant classes', () => {
    render(<Button variant="danger">Delete</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('bg-red-600')
  })

  it('applies size classes', () => {
    render(<Button size="lg">Large</Button>)
    const button = screen.getByRole('button')
    expect(button).toHaveClass('px-6', 'py-3', 'text-lg')
  })

  it('disables button when disabled', () => {
    render(<Button disabled>Disabled</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    // Tailwind applies these classes via disabled: pseudo-class, not statically
    expect(button).toHaveAttribute('disabled')
  })
})

describe('Input', () => {
  it('renders label', () => {
    render(<Input label="Email" value="" onChange={() => {}} />)
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
  })

  it('shows error message', () => {
    render(<Input label="Email" value="" onChange={() => {}} error="Invalid email" />)
    expect(screen.getByText('Invalid email')).toBeInTheDocument()
  })

  it('calls onChange with value', () => {
    const handleChange = vi.fn()
    render(<Input value="" onChange={handleChange} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } })
    expect(handleChange).toHaveBeenCalledWith('test')
  })
})

describe('Card', () => {
  it('renders children', () => {
    render(<Card>Card content</Card>)
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  it('applies click handler', () => {
    const handleClick = vi.fn()
    render(<Card onClick={handleClick}>Clickable</Card>)
    fireEvent.click(screen.getByText('Clickable'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
})

describe('Modal', () => {
  it('does not render when closed', () => {
    render(<Modal isOpen={false} onClose={() => {}} title="Test">Content</Modal>)
    expect(screen.queryByText('Test')).not.toBeInTheDocument()
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('renders when open', () => {
    render(<Modal isOpen={true} onClose={() => {}} title="Test">Content</Modal>)
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
  })
  it('calls onClose when clicking backdrop', () => {
    const handleClose = vi.fn()
    render(<Modal isOpen={true} onClose={handleClose} title="Test">Content</Modal>)
    // Click on the backdrop
    const backdrop = screen.getByTestId('modal-backdrop')
    fireEvent.click(backdrop)
    expect(handleClose).toHaveBeenCalledTimes(1)
  })
})

describe('Badge', () => {
  it('renders children', () => {
    render(<Badge>New</Badge>)
    expect(screen.getByText('New')).toBeInTheDocument()
  })

  it('applies variant classes', () => {
    render(<Badge variant="success">Success</Badge>)
    expect(screen.getByText('Success')).toHaveClass('bg-green-100')
  })
})

describe('LoadingSpinner', () => {
  it('renders spinner', () => {
    render(<LoadingSpinner />)
    expect(screen.getByRole('img')).toBeInTheDocument()
  })

  it('applies size classes', () => {
    render(<LoadingSpinner size="lg" />)
    expect(screen.getByRole('img')).toHaveClass('w-12', 'h-12')
  })
})

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState icon={<span>📦</span>} title="No items" description="Create one" />)
    expect(screen.getByText('No items')).toBeInTheDocument()
    expect(screen.getByText('Create one')).toBeInTheDocument()
  })

  it('renders action', () => {
    const action = <button>Action</button>
    render(<EmptyState icon={<span>📦</span>} title="No items" action={action} />)
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('renders error message', () => {
    render(<ErrorState message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('renders retry button when onRetry provided', () => {
    const handleRetry = vi.fn()
    render(<ErrorState message="Error" onRetry={handleRetry} />)
    expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(handleRetry).toHaveBeenCalledTimes(1)
  })
})