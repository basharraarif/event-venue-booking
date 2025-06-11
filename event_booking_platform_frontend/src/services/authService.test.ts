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
    it('should call POST /auth/logout/ and remove token from localStorage', async () => {
      localStorage.setItem('authToken', 'testtoken');
      mockedAxiosInstance.post.mockResolvedValueOnce({ data: {} }); // Logout usually returns empty or success message

      await logout('testtoken'); // Pass token to logout

      expect(mockedAxiosInstance.post).toHaveBeenCalledWith('/auth/logout/');
      expect(localStorage.getItem('authToken')).toBeNull();
    });

    it('should remove token from localStorage even if API call fails (best effort)', async () => {
        localStorage.setItem('authToken', 'testtoken');
        mockedAxiosInstance.post.mockRejectedValueOnce(new Error('Logout API Failed'));

        await expect(logout('testtoken')).rejects.toThrow('Logout API Failed'); // Error should still propagate
        expect(localStorage.getItem('authToken')).toBeNull(); // Token should be cleared regardless
      });
  });

  describe('getCurrentUser', () => {
    it('should call GET /auth/user/ with token and return user data', async () => {
      const token = 'testtoken';
      const mockUser = { id: '1', username: 'testuser', email: 'test@example.com' };
      mockedAxiosInstance.get.mockResolvedValueOnce({ data: mockUser });

      const result = await getCurrentUser(token);

      expect(mockedAxiosInstance.get).toHaveBeenCalledWith('/auth/user/', {
        headers: { Authorization: `Token ${token}` },
      });
      expect(result).toEqual(mockUser);
    });

    it('should throw error if API call fails for getCurrentUser', async () => {
      const token = 'testtoken';
      mockedAxiosInstance.get.mockRejectedValueOnce(new Error('Fetch User Failed'));
      await expect(getCurrentUser(token)).rejects.toThrow('Fetch User Failed');
    });
  });
});
