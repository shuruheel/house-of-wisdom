export class AppError extends Error {
    constructor(public code: string, message: string) {
      super(message);
      this.name = 'AppError';
    }
  }
  
  export function handleError(error: unknown, context: string): AppError {
    console.error(`Error in ${context}:`, error);
    
    if (error instanceof AppError) {
      return error;
    }
    
    if (error instanceof Error) {
      return new AppError('UNKNOWN_ERROR', `${context}: ${error.message}`);
    }
    
    return new AppError('UNKNOWN_ERROR', `${context}: An unknown error occurred`);
  }