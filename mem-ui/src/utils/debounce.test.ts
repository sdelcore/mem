import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { debounce } from './debounce'

describe('debounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('delays function execution', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 100)

    debouncedFn()
    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
  })

  it('cancels previous calls when called multiple times', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 100)

    debouncedFn('first')
    vi.advanceTimersByTime(50)
    debouncedFn('second')
    vi.advanceTimersByTime(50)
    debouncedFn('third')

    expect(fn).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('third')
  })

  it('preserves function arguments', () => {
    const fn = vi.fn()
    const debouncedFn = debounce(fn, 100)

    debouncedFn('arg1', 'arg2', 123)
    vi.advanceTimersByTime(100)

    expect(fn).toHaveBeenCalledWith('arg1', 'arg2', 123)
  })

  it('preserves this context', () => {
    const originalMethod = vi.fn(function(this: any) {
      return this.value
    })

    const obj = {
      value: 'test',
      method: debounce(originalMethod, 100)
    }

    obj.method()

    vi.advanceTimersByTime(100)
    expect(originalMethod).toHaveBeenCalled()
  })

  it('allows multiple independent debounced functions', () => {
    const fn1 = vi.fn()
    const fn2 = vi.fn()
    const debouncedFn1 = debounce(fn1, 100)
    const debouncedFn2 = debounce(fn2, 200)

    debouncedFn1()
    debouncedFn2()

    vi.advanceTimersByTime(100)
    expect(fn1).toHaveBeenCalledTimes(1)
    expect(fn2).not.toHaveBeenCalled()

    vi.advanceTimersByTime(100)
    expect(fn1).toHaveBeenCalledTimes(1)
    expect(fn2).toHaveBeenCalledTimes(1)
  })
})