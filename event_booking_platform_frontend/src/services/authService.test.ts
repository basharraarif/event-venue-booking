import { login, register, logout, getCurrentUser, LoginCredentials, RegistrationData } from './authService';
import axiosInstance from './axiosInstance';

jest.mock('./axiosInstance');
const mockedAxiosInstance = axiosInstance as jest.Mocked<typeof axiosInstance>;

describe('authService', () => {
  afterEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  describe('login', () => {
    it('should call POST /auth/login/ with credentials and return data', async () => {
      const credentials: LoginCredentials = { email: 'test@example.com', password: 'password' };
      const mockResponse = { key: 'testtoken' };
      mockedAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await login(credentials);

      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/auth/login/', credentials);
      expect(result).toEqual(mockResponse);
    });

    it('should throw error if API call fails for login', async () => {
      const credentials: LoginCredentials = { email: 'test@example.com', password: 'password' };
      mockedAxiosInstance.post.mockRejectedValueOnce(new Error('Login Failed'));
      await expect(login(credentials)).rejects.toThrow('Login Failed');
    });
  });

  describe('register', () => {
    it('should call POST /auth/registration/ with data and return data', async () => {
      const regData: RegistrationData = { username: 'newuser', email: 'new@example.com', password: 'password123', password2: 'password123' };
      const mockResponse = { detail: 'Registration successful' }; // Example response
      mockedAxiosInstance.post.mockResolvedValueOnce({ data: mockResponse });

      const result = await register(regData);

      // dj-rest-auth registration endpoint might expect password1 and password2
      // authService maps 'password' to 'password1' and includes 'password2'
      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/auth/registration/', {
        username: regData.username,
        email: regData.email,
        password: regData.password, // authService might map this to password1
        password2: regData.password2,
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error if API call fails for register', async () => {
      const regData: RegistrationData = { username: 'newuser', email: 'new@example.com', password: 'password123', password2: 'password123' };
      mockedAxiosInstance.post.mockRejectedValueOnce(new Error('Registration Failed'));
      await expect(register(regData)).rejects.toThrow('Registration Failed');
    });
  });

  describe('logout', () => {
    it('should call POST /auth/logout/', async () => {
      mockedAxiosInstance.post.mockResolvedValueOnce({ data: {} });

      await logout(null); // Token is handled by interceptor, pass null or don't pass if argument removed

      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/auth/logout/', null);
      // localStorage interaction is handled by AuthContext, not service.
    });

    it('should propagate error if API call fails for logout', async () => {
        mockedAxiosInstance.post.mockRejectedValueOnce(new Error('Logout API Failed'));
        // Token is handled by interceptor
        await expect(logout(null)).rejects.toThrow('Logout API Failed');
      });
  });

  describe('getCurrentUser', () => {
    it('should call GET /auth/user/ and return user data', async () => {
      const mockUser = { pk: 1, id: 1, username: 'testuser', email: 'test@example.com', roles: [] };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: { pk: 1, username: 'testuser', email: 'test@example.com', roles: []} });

      const result = await getCurrentUser(); // Token is handled by interceptor

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith('/auth/user/');
      // Service maps pk to id
      expect(result).toEqual(mockUser);
    });

    it('should correctly map pk to id if id is missing in getCurrentUser response', async () => {
      const mockUserFromApi = { pk: 123, username: 'testpk', email: 'pk@example.com', roles: ['CUSTOMER'] };
      const expectedUser = { ...mockUserFromApi, id: 123 };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockUserFromApi });

      const result = await getCurrentUser();
      expect(result).toEqual(expectedUser);
    });

    it('should throw error if API call fails for getCurrentUser', async () => {
      mockedAxiosInstance.get.mockRejectedValueOnce(new Error('Fetch User Failed'));
      await expect(getCurrentUser()).rejects.toThrow('Fetch User Failed');
    });
  });
});
