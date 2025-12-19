# HDI API - Mobile App Integration

Module API cho phép kết nối Odoo với Mobile App sử dụng JWT Token authentication.

## Cài đặt

### 1. Cài đặt Dependencies

Cài đặt PyJWT library:
```bash
pip install pyjwt
```

### 2. Cấu hình Secret Key

Trong Odoo, đi đến **Settings > Technical > Parameters**:
- Tạo parameter: `hdi_api.jwt_secret_key`
- Value: Một chuỗi secret key mạnh (ví dụ: `your-very-long-secret-key-min-32-chars`)

> ⚠️ **Bảo mật:** Đổi secret key trong production, không sử dụng default key!

### 3. Cài đặt Module

1. Cập nhật danh sách module: Odoo > Apps > Update Apps List
2. Tìm "HDI API" và click **Install**

---

## API Endpoints

### 1. Đăng nhập (POST /api/v1/auth/login)

**URL:** `POST /api/v1/auth/login`

**Request:**
```json
{
    "login": "admin@example.com",
    "password": "password123"
}
```

**Response (Success - 200):**
```json
{
    "status": "success",
    "message": "Đăng nhập thành công",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "name": "Administrator",
        "email": "admin@example.com",
        "login": "admin@example.com"
    }
}
```

**Response (Error - 401):**
```json
{
    "status": "error",
    "message": "Tài khoản hoặc mật khẩu không chính xác"
}
```

---

### 2. Lấy thông tin người dùng hiện tại (GET /api/v1/auth/me)

**URL:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response (Success - 200):**
```json
{
    "status": "success",
    "user": {
        "id": 1,
        "name": "Administrator",
        "email": "admin@example.com",
        "login": "admin@example.com"
    }
}
```

**Response (Error - 401):**
```json
{
    "status": "error",
    "message": "Token không được cung cấp"
}
```

---

### 3. Xác minh Token (POST /api/v1/auth/verify-token)

**URL:** `POST /api/v1/auth/verify-token`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response (Success - 200):**
```json
{
    "status": "success",
    "valid": true,
    "user": {
        "id": 1,
        "name": "Administrator",
        "email": "admin@example.com",
        "login": "admin@example.com"
    }
}
```

---

### 4. Làm mới Token (POST /api/v1/auth/refresh-token)

**URL:** `POST /api/v1/auth/refresh-token`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response (Success - 200):**
```json
{
    "status": "success",
    "message": "Làm mới token thành công",
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

---

### 5. Đăng xuất (POST /api/v1/auth/logout)

**URL:** `POST /api/v1/auth/logout`

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Response (Success - 200):**
```json
{
    "status": "success",
    "message": "Đã đăng xuất thành công"
}
```

---

## Sử dụng trong Mobile App

### Flutter Example

```dart
import 'package:http/http.dart' as http;
import 'dart:convert';

class OdooAuthService {
  final String baseUrl = 'http://your-odoo-server.com';

  Future<String?> login(String email, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'login': email,
          'password': password,
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['token']; // Lưu token này
      } else {
        print('Login failed: ${response.body}');
      }
    } catch (e) {
      print('Error: $e');
    }
    return null;
  }

  Future<bool> verifyToken(String token) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/auth/verify-token'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      return response.statusCode == 200;
    } catch (e) {
      print('Error: $e');
    }
    return false;
  }

  Future<Map<String, dynamic>?> getCurrentUser(String token) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/v1/auth/me'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['user'];
      }
    } catch (e) {
      print('Error: $e');
    }
    return null;
  }
}
```

### React Native Example

```javascript
const login = async (email, password) => {
  try {
    const response = await fetch('http://your-odoo-server.com/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        login: email,
        password: password,
      }),
    });

    const data = await response.json();
    if (response.ok) {
      // Lưu token
      await AsyncStorage.setItem('authToken', data.token);
      return data.user;
    } else {
      throw new Error(data.message);
    }
  } catch (error) {
    console.error('Login error:', error);
  }
};

const getCurrentUser = async (token) => {
  try {
    const response = await fetch('http://your-odoo-server.com/api/v1/auth/me', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    if (response.ok) {
      return data.user;
    }
  } catch (error) {
    console.error('Error:', error);
  }
};
```

---

## Thông tin JWT Token

- **Thời gian hết hạn (Expiration):** 30 ngày từ lúc tạo
- **Algorithm:** HS256
- **Payload:**
  - `user_id`: ID của user
  - `login`: Login username/email
  - `name`: Tên đầy đủ
  - `email`: Email address
  - `iat`: Issued at (Unix timestamp)
  - `exp`: Expiration (Unix timestamp)

---

## Kiểm tra API bằng cURL

### Đăng nhập:
```bash
curl -X POST http://localhost:8069/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin"}'
```

### Lấy thông tin user hiện tại:
```bash
curl -X GET http://localhost:8069/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Xác minh token:
```bash
curl -X POST http://localhost:8069/api/v1/auth/verify-token \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách khắc phục |
|-----|-----------|-----------------|
| `Token không được cung cấp` | Thiếu Authorization header | Thêm `Authorization: Bearer <token>` |
| `Token đã hết hạn` | Token lâu hơn 30 ngày | Gọi `/api/v1/auth/refresh-token` |
| `Token không hợp lệ` | Secret key không khớp hoặc token corrupt | Kiểm tra secret key config |
| `Tài khoản hoặc mật khẩu không chính xác` | Sai login/password | Kiểm tra lại credentials |

---

## Bảo mật

1. **Luôn sử dụng HTTPS** trong production
2. **Đổi secret key** mạnh (tối thiểu 32 ký tự)
3. **Lưu token an toàn** ở phía client (không lưu trong localStorage)
4. **Token expiration:** Tự động hết hạn sau 30 ngày
5. **Refresh token:** Dùng `/api/v1/auth/refresh-token` để gia hạn quyền truy cập

---

## Hỗ trợ

Nếu có vấn đề, kiểm tra logs trong Odoo:
```
Settings > Technical > Logs > Error Logs
```
