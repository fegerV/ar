# 📱 Vertex AR Mobile SDK - Примеры для всех платформ

Полные рабочие примеры интеграции для iOS, Android, Flutter, React Native и Web.

---

## 📋 Оглавление

1. [iOS (Swift)](#ios-swift)
2. [Android (Kotlin)](#android-kotlin)
3. [Flutter (Dart)](#flutter-dart)
4. [React Native (TypeScript)](#react-native-typescript)
5. [Web (TypeScript)](#web-typescript)

---

## iOS (Swift)

### Инициализация клиента

```swift
import Foundation
import Combine

// MARK: - Models
struct AuthToken: Codable {
  let access_token: String
  let token_type: String
}

struct Client: Codable, Identifiable {
  let id: String
  let phone: String
  let name: String
  let created_at: String
}

struct Portrait: Codable, Identifiable {
  let id: String
  let client_id: String
  let permanent_link: String
  let qr_code_base64: String?
  let image_path: String
  let view_count: Int
  let created_at: String
}

// MARK: - Network Manager
class VertexARNetworkManager: NSObject, URLSessionDelegate {
  static let shared = VertexARNetworkManager()
  
  let baseURL = "https://api.vertex-ar.com"
  private var token: String?
  
  private let session: URLSession
  
  override init() {
    let config = URLSessionConfiguration.default
    config.timeoutIntervalForRequest = 30
    config.timeoutIntervalForResource = 60
    config.waitsForConnectivity = true
    session = URLSession(configuration: config)
    super.init()
  }
  
  // MARK: - Authentication
  
  func login(username: String, password: String) async throws -> AuthToken {
    let endpoint = "\(baseURL)/auth/login"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let loginData = ["username": username, "password": password]
    request.httpBody = try JSONEncoder().encode(loginData)
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse else {
      throw NetworkError.invalidResponse
    }
    
    guard (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.serverError(httpResponse.statusCode)
    }
    
    let token = try JSONDecoder().decode(AuthToken.self, from: data)
    self.token = token.access_token
    
    // Save to Keychain
    try saveTokenToKeychain(token.access_token)
    
    return token
  }
  
  func logout() async throws {
    let endpoint = "\(baseURL)/auth/logout"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    addAuthHeader(to: &request)
    
    let (_, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    token = nil
    try clearTokenFromKeychain()
  }
  
  // MARK: - Clients
  
  func createClient(phone: String, name: String) async throws -> Client {
    let endpoint = "\(baseURL)/clients/"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    addAuthHeader(to: &request)
    
    let clientData: [String: String] = [
      "phone": phone,
      "name": name,
      "company_id": "vertex-ar-default"
    ]
    request.httpBody = try JSONEncoder().encode(clientData)
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    return try JSONDecoder().decode(Client.self, from: data)
  }
  
  func getClients(page: Int = 1, pageSize: Int = 50) async throws -> [Client] {
    let endpoint = "\(baseURL)/clients/?page=\(page)&page_size=\(pageSize)"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "GET"
    addAuthHeader(to: &request)
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    struct ListResponse: Codable {
      let items: [Client]
    }
    
    let listResponse = try JSONDecoder().decode(ListResponse.self, from: data)
    return listResponse.items
  }
  
  func getClient(id: String) async throws -> Client {
    let endpoint = "\(baseURL)/clients/\(id)"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "GET"
    addAuthHeader(to: &request)
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    return try JSONDecoder().decode(Client.self, from: data)
  }
  
  func updateClient(id: String, phone: String?, name: String?) async throws -> Client {
    let endpoint = "\(baseURL)/clients/\(id)"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "PUT"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    addAuthHeader(to: &request)
    
    var updateData: [String: String?] = [:]
    if let phone = phone { updateData["phone"] = phone }
    if let name = name { updateData["name"] = name }
    
    request.httpBody = try JSONEncoder().encode(updateData)
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    return try JSONDecoder().decode(Client.self, from: data)
  }
  
  func deleteClient(id: String) async throws {
    let endpoint = "\(baseURL)/clients/\(id)"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "DELETE"
    addAuthHeader(to: &request)
    
    let (_, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
  }
  
  // MARK: - Portraits
  
  func uploadPortrait(clientId: String, imageData: Data) async throws -> Portrait {
    let endpoint = "\(baseURL)/portraits/"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    addAuthHeader(to: &request)
    
    let boundary = "----WebKitFormBoundary\(UUID().uuidString)"
    request.setValue(
      "multipart/form-data; boundary=\(boundary)",
      forHTTPHeaderField: "Content-Type"
    )
    
    var body = Data()
    
    // Add client_id field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"client_id\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(clientId)\r\n".data(using: .utf8)!)
    
    // Add image field
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append(
      "Content-Disposition: form-data; name=\"image\"; filename=\"portrait.jpg\"\r\n".data(using: .utf8)!
    )
    body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
    body.append(imageData)
    body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)
    
    request.httpBody = body
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    return try JSONDecoder().decode(Portrait.self, from: data)
  }
  
  func getPortraits(clientId: String, page: Int = 1) async throws -> [Portrait] {
    let endpoint = "\(baseURL)/portraits/?client_id=\(clientId)&page=\(page)"
    guard let url = URL(string: endpoint) else {
      throw NetworkError.invalidURL
    }
    
    var request = URLRequest(url: url)
    request.httpMethod = "GET"
    addAuthHeader(to: &request)
    
    let (data, response) = try await session.data(for: request)
    
    guard let httpResponse = response as? HTTPURLResponse,
          (200...299).contains(httpResponse.statusCode) else {
      throw NetworkError.invalidResponse
    }
    
    struct ListResponse: Codable {
      let items: [Portrait]
    }
    
    let listResponse = try JSONDecoder().decode(ListResponse.self, from: data)
    return listResponse.items
  }
  
  // MARK: - Helper Methods
  
  private func addAuthHeader(to request: inout URLRequest) {
    if let token = token {
      request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
    }
  }
  
  private func saveTokenToKeychain(_ token: String) throws {
    let query: [String: Any] = [
      kSecClass as String: kSecClassGenericPassword,
      kSecAttrAccount as String: "vertex_ar_token",
      kSecValueData as String: token.data(using: .utf8) ?? Data()
    ]
    
    SecItemDelete(query as CFDictionary)
    let status = SecItemAdd(query as CFDictionary, nil)
    
    guard status == errSecSuccess else {
      throw NetworkError.keychainError
    }
  }
  
  private func clearTokenFromKeychain() throws {
    let query: [String: Any] = [
      kSecClass as String: kSecClassGenericPassword,
      kSecAttrAccount as String: "vertex_ar_token"
    ]
    
    let status = SecItemDelete(query as CFDictionary)
    guard status == errSecSuccess else {
      throw NetworkError.keychainError
    }
  }
}

// MARK: - Error Types
enum NetworkError: LocalizedError {
  case invalidURL
  case invalidResponse
  case serverError(Int)
  case decodingError
  case keychainError
  
  var errorDescription: String? {
    switch self {
    case .invalidURL:
      return "Invalid URL"
    case .invalidResponse:
      return "Invalid server response"
    case .serverError(let code):
      return "Server error: \(code)"
    case .decodingError:
      return "Failed to decode response"
    case .keychainError:
      return "Keychain operation failed"
    }
  }
}

// MARK: - ViewModel (MVVM Pattern)
@MainActor
class VertexARViewModel: ObservableObject {
  @Published var clients: [Client] = []
  @Published var isLoading = false
  @Published var errorMessage: String?
  
  private let networkManager = VertexARNetworkManager.shared
  
  func login(username: String, password: String) async {
    isLoading = true
    defer { isLoading = false }
    
    do {
      let token = try await networkManager.login(username: username, password: password)
      print("Login successful: \(token.access_token)")
    } catch {
      errorMessage = error.localizedDescription
    }
  }
  
  func fetchClients() async {
    isLoading = true
    defer { isLoading = false }
    
    do {
      clients = try await networkManager.getClients()
    } catch {
      errorMessage = error.localizedDescription
    }
  }
  
  func createClient(phone: String, name: String) async {
    isLoading = true
    defer { isLoading = false }
    
    do {
      let newClient = try await networkManager.createClient(phone: phone, name: name)
      clients.append(newClient)
    } catch {
      errorMessage = error.localizedDescription
    }
  }
}

// MARK: - SwiftUI View
struct ContentView: View {
  @StateObject private var viewModel = VertexARViewModel()
  @State private var showingNewClientForm = false
  @State private var phone = ""
  @State private var name = ""
  
  var body: some View {
    NavigationView {
      List {
        ForEach(viewModel.clients) { client in
          HStack {
            VStack(alignment: .leading) {
              Text(client.name)
                .font(.headline)
              Text(client.phone)
                .font(.caption)
                .foregroundColor(.gray)
            }
            Spacer()
            Text(client.created_at)
              .font(.caption)
              .foregroundColor(.gray)
          }
        }
      }
      .navigationTitle("Clients")
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Button(action: { showingNewClientForm.toggle() }) {
            Image(systemName: "plus.circle.fill")
          }
        }
      }
      .sheet(isPresented: $showingNewClientForm) {
        NewClientForm { newPhone, newName in
          phone = newPhone
          name = newName
          Task {
            await viewModel.createClient(phone: phone, name: name)
            showingNewClientForm = false
          }
        }
      }
      .task {
        await viewModel.fetchClients()
      }
    }
  }
}

struct NewClientForm: View {
  @Environment(\.dismiss) var dismiss
  @State private var phone = ""
  @State private var name = ""
  let onSave: (String, String) -> Void
  
  var body: some View {
    NavigationView {
      Form {
        TextField("Phone", text: $phone)
        TextField("Name", text: $name)
      }
      .navigationTitle("New Client")
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Button("Save") {
            onSave(phone, name)
          }
        }
      }
    }
  }
}
```

---

## Android (Kotlin)

### Инициализация клиента

```kotlin
package com.vertexar.mobile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import com.google.gson.annotations.SerializedName
import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.util.concurrent.TimeUnit

// MARK: - Models
data class AuthTokenResponse(
  @SerializedName("access_token")
  val accessToken: String,
  @SerializedName("token_type")
  val tokenType: String
)

data class ClientResponse(
  val id: String,
  val phone: String,
  val name: String,
  val created_at: String
)

data class ClientsListResponse(
  val items: List<ClientResponse>,
  val total: Int,
  val page: Int,
  val page_size: Int
)

data class PortraitResponse(
  val id: String,
  val client_id: String,
  val permanent_link: String,
  val qr_code_base64: String?,
  val image_path: String,
  val view_count: Int,
  val created_at: String
)

// MARK: - API Service
interface VertexARService {
  @POST("/auth/login")
  suspend fun login(@Body request: LoginRequest): AuthTokenResponse
  
  @POST("/auth/logout")
  suspend fun logout(): Unit
  
  @POST("/clients/")
  suspend fun createClient(@Body request: CreateClientRequest): ClientResponse
  
  @GET("/clients/")
  suspend fun getClients(
    @Query("page") page: Int = 1,
    @Query("page_size") pageSize: Int = 50
  ): ClientsListResponse
  
  @GET("/clients/{id}")
  suspend fun getClient(@Path("id") id: String): ClientResponse
  
  @PUT("/clients/{id}")
  suspend fun updateClient(
    @Path("id") id: String,
    @Body request: UpdateClientRequest
  ): ClientResponse
  
  @DELETE("/clients/{id}")
  suspend fun deleteClient(@Path("id") id: String): Unit
  
  @Multipart
  @POST("/portraits/")
  suspend fun uploadPortrait(
    @Part("client_id") clientId: okhttp3.RequestBody,
    @Part image: okhttp3.MultipartBody.Part
  ): PortraitResponse
}

data class LoginRequest(
  val username: String,
  val password: String
)

data class CreateClientRequest(
  val phone: String,
  val name: String,
  val company_id: String = "vertex-ar-default"
)

data class UpdateClientRequest(
  val phone: String? = null,
  val name: String? = null
)

// MARK: - Token Storage
class SecureTokenStorage(context: Context) {
  private val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()
  
  private val sharedPreferences = EncryptedSharedPreferences.create(
    context,
    "vertex_ar_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
  )
  
  fun saveToken(token: String) {
    sharedPreferences.edit().putString("auth_token", token).apply()
  }
  
  fun getToken(): String? {
    return sharedPreferences.getString("auth_token", null)
  }
  
  fun clearToken() {
    sharedPreferences.edit().remove("auth_token").apply()
  }
}

// MARK: - API Client
class VertexARClient(
  private val context: Context,
  private val baseUrl: String = "https://api.vertex-ar.com"
) {
  private val tokenStorage = SecureTokenStorage(context)
  private var token: String? = null
  
  private val httpClient = OkHttpClient.Builder()
    .connectTimeout(30, TimeUnit.SECONDS)
    .readTimeout(30, TimeUnit.SECONDS)
    .writeTimeout(30, TimeUnit.SECONDS)
    .addInterceptor { chain ->
      val originalRequest = chain.request()
      val requestBuilder = originalRequest.newBuilder()
      
      token?.let {
        requestBuilder.addHeader("Authorization", "Bearer $it")
      }
      
      val newRequest = requestBuilder.build()
      chain.proceed(newRequest)
    }
    .build()
  
  private val retrofit = Retrofit.Builder()
    .baseUrl(baseUrl)
    .addConverterFactory(GsonConverterFactory.create())
    .client(httpClient)
    .build()
  
  private val service = retrofit.create(VertexARService::class.java)
  
  init {
    token = tokenStorage.getToken()
  }
  
  // MARK: - Authentication
  
  suspend fun login(username: String, password: String): AuthTokenResponse {
    return withContext(Dispatchers.IO) {
      val request = LoginRequest(username, password)
      val response = service.login(request)
      token = response.accessToken
      tokenStorage.saveToken(response.accessToken)
      response
    }
  }
  
  suspend fun logout() {
    return withContext(Dispatchers.IO) {
      service.logout()
      token = null
      tokenStorage.clearToken()
    }
  }
  
  // MARK: - Clients
  
  suspend fun createClient(phone: String, name: String): ClientResponse {
    return withContext(Dispatchers.IO) {
      val request = CreateClientRequest(phone, name)
      service.createClient(request)
    }
  }
  
  suspend fun getClients(page: Int = 1, pageSize: Int = 50): ClientsListResponse {
    return withContext(Dispatchers.IO) {
      service.getClients(page, pageSize)
    }
  }
  
  suspend fun getClient(id: String): ClientResponse {
    return withContext(Dispatchers.IO) {
      service.getClient(id)
    }
  }
  
  suspend fun updateClient(id: String, phone: String? = null, name: String? = null): ClientResponse {
    return withContext(Dispatchers.IO) {
      val request = UpdateClientRequest(phone, name)
      service.updateClient(id, request)
    }
  }
  
  suspend fun deleteClient(id: String) {
    return withContext(Dispatchers.IO) {
      service.deleteClient(id)
    }
  }
  
  // MARK: - Portraits
  
  suspend fun uploadPortrait(clientId: String, imageData: ByteArray): PortraitResponse {
    return withContext(Dispatchers.IO) {
      val clientIdBody = clientId.toRequestBody("text/plain".toMediaType())
      val imageBody = imageData.toRequestBody("image/jpeg".toMediaType())
      val imagePart = okhttp3.MultipartBody.Part.createFormData(
        "image",
        "portrait.jpg",
        imageBody
      )
      
      service.uploadPortrait(clientIdBody, imagePart)
    }
  }
}

// MARK: - ViewModel
class VertexARViewModel(
  private val client: VertexARClient
) : ViewModel() {
  
  private val _clients = MutableStateFlow<List<ClientResponse>>(emptyList())
  val clients: StateFlow<List<ClientResponse>> = _clients
  
  private val _isLoading = MutableStateFlow(false)
  val isLoading: StateFlow<Boolean> = _isLoading
  
  private val _error = MutableStateFlow<String?>(null)
  val error: StateFlow<String?> = _error
  
  // MARK: - Public Methods
  
  fun login(username: String, password: String) {
    viewModelScope.launch {
      _isLoading.value = true
      try {
        val token = client.login(username, password)
        println("Login successful: ${token.accessToken}")
      } catch (e: Exception) {
        _error.value = e.message
      } finally {
        _isLoading.value = false
      }
    }
  }
  
  fun fetchClients() {
    viewModelScope.launch {
      _isLoading.value = true
      try {
        val response = client.getClients()
        _clients.value = response.items
      } catch (e: Exception) {
        _error.value = e.message
      } finally {
        _isLoading.value = false
      }
    }
  }
  
  fun createClient(phone: String, name: String) {
    viewModelScope.launch {
      _isLoading.value = true
      try {
        val newClient = client.createClient(phone, name)
        _clients.value = _clients.value + newClient
      } catch (e: Exception) {
        _error.value = e.message
      } finally {
        _isLoading.value = false
      }
    }
  }
}

// MARK: - Compose UI
@Composable
fun VertexARScreen(viewModel: VertexARViewModel) {
  val clients by viewModel.clients.collectAsState()
  val isLoading by viewModel.isLoading.collectAsState()
  val error by viewModel.error.collectAsState()
  
  Column(modifier = Modifier.fillMaxSize()) {
    if (isLoading) {
      CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
    }
    
    error?.let {
      Text(it, color = Color.Red)
    }
    
    LazyColumn {
      items(clients) { client ->
        ClientCard(client)
      }
    }
  }
}

@Composable
fun ClientCard(client: ClientResponse) {
  Card(modifier = Modifier
    .fillMaxWidth()
    .padding(8.dp)) {
    Column(modifier = Modifier.padding(16.dp)) {
      Text(client.name, fontWeight = FontWeight.Bold)
      Text(client.phone, fontSize = 12.sp)
      Text(client.created_at, fontSize = 10.sp, color = Color.Gray)
    }
  }
}
```

---

## Flutter (Dart)

### Полный пример приложения

```dart
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import 'package:provider/provider.dart';

// MARK: - Constants
class APIConfig {
  static const String baseUrl = 'https://api.vertex-ar.com';
  static const Duration timeout = Duration(seconds: 30);
}

// MARK: - Models
class AuthToken {
  final String accessToken;
  final String tokenType;
  
  AuthToken({
    required this.accessToken,
    required this.tokenType,
  });
  
  factory AuthToken.fromJson(Map<String, dynamic> json) {
    return AuthToken(
      accessToken: json['access_token'] ?? '',
      tokenType: json['token_type'] ?? 'bearer',
    );
  }
}

class ClientModel {
  final String id;
  final String phone;
  final String name;
  final String createdAt;
  
  ClientModel({
    required this.id,
    required this.phone,
    required this.name,
    required this.createdAt,
  });
  
  factory ClientModel.fromJson(Map<String, dynamic> json) {
    return ClientModel(
      id: json['id'] ?? '',
      phone: json['phone'] ?? '',
      name: json['name'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }
}

class ClientsList {
  final List<ClientModel> items;
  final int total;
  final int page;
  final int pageSize;
  
  ClientsList({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
  });
  
  factory ClientsList.fromJson(Map<String, dynamic> json) {
    return ClientsList(
      items: (json['items'] as List<dynamic>?)
          ?.map((item) => ClientModel.fromJson(item as Map<String, dynamic>))
          .toList() ?? [],
      total: json['total'] ?? 0,
      page: json['page'] ?? 1,
      pageSize: json['page_size'] ?? 50,
    );
  }
}

class PortraitModel {
  final String id;
  final String clientId;
  final String permanentLink;
  final String? qrCodeBase64;
  final String imagePath;
  final int viewCount;
  final String createdAt;
  
  PortraitModel({
    required this.id,
    required this.clientId,
    required this.permanentLink,
    this.qrCodeBase64,
    required this.imagePath,
    required this.viewCount,
    required this.createdAt,
  });
  
  factory PortraitModel.fromJson(Map<String, dynamic> json) {
    return PortraitModel(
      id: json['id'] ?? '',
      clientId: json['client_id'] ?? '',
      permanentLink: json['permanent_link'] ?? '',
      qrCodeBase64: json['qr_code_base64'],
      imagePath: json['image_path'] ?? '',
      viewCount: json['view_count'] ?? 0,
      createdAt: json['created_at'] ?? '',
    );
  }
}

// MARK: - API Service
class VertexARService {
  final _secureStorage = const FlutterSecureStorage();
  String? _token;
  
  VertexARService() {
    _loadToken();
  }
  
  Future<void> _loadToken() async {
    _token = await _secureStorage.read(key: 'vertex_ar_token');
  }
  
  Future<void> _saveToken(String token) async {
    _token = token;
    await _secureStorage.write(key: 'vertex_ar_token', value: token);
  }
  
  Map<String, String> _getHeaders({bool requireAuth = true}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    
    if (requireAuth && _token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    
    return headers;
  }
  
  // MARK: - Authentication
  
  Future<AuthToken> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('${APIConfig.baseUrl}/auth/login'),
        headers: _getHeaders(requireAuth: false),
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
        timeout: APIConfig.timeout,
      ).timeout(APIConfig.timeout);
      
      if (response.statusCode == 200) {
        final token = AuthToken.fromJson(jsonDecode(response.body));
        await _saveToken(token.accessToken);
        return token;
      } else {
        throw Exception('Login failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Login error: $e');
    }
  }
  
  Future<void> logout() async {
    try {
      await http.post(
        Uri.parse('${APIConfig.baseUrl}/auth/logout'),
        headers: _getHeaders(),
        timeout: APIConfig.timeout,
      ).timeout(APIConfig.timeout);
      
      _token = null;
      await _secureStorage.delete(key: 'vertex_ar_token');
    } catch (e) {
      throw Exception('Logout error: $e');
    }
  }
  
  // MARK: - Clients
  
  Future<ClientsList> getClients({int page = 1, int pageSize = 50}) async {
    try {
      final response = await http.get(
        Uri.parse(
          '${APIConfig.baseUrl}/clients/?page=$page&page_size=$pageSize'
        ),
        headers: _getHeaders(),
        timeout: APIConfig.timeout,
      ).timeout(APIConfig.timeout);
      
      if (response.statusCode == 200) {
        return ClientsList.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to fetch clients: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Get clients error: $e');
    }
  }
  
  Future<ClientModel> createClient(String phone, String name) async {
    try {
      final response = await http.post(
        Uri.parse('${APIConfig.baseUrl}/clients/'),
        headers: _getHeaders(),
        body: jsonEncode({
          'phone': phone,
          'name': name,
          'company_id': 'vertex-ar-default',
        }),
        timeout: APIConfig.timeout,
      ).timeout(APIConfig.timeout);
      
      if (response.statusCode == 201) {
        return ClientModel.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to create client: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Create client error: $e');
    }
  }
  
  Future<ClientModel> updateClient(
    String id, {
    String? phone,
    String? name,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (phone != null) body['phone'] = phone;
      if (name != null) body['name'] = name;
      
      final response = await http.put(
        Uri.parse('${APIConfig.baseUrl}/clients/$id'),
        headers: _getHeaders(),
        body: jsonEncode(body),
        timeout: APIConfig.timeout,
      ).timeout(APIConfig.timeout);
      
      if (response.statusCode == 200) {
        return ClientModel.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to update client: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Update client error: $e');
    }
  }
  
  Future<void> deleteClient(String id) async {
    try {
      final response = await http.delete(
        Uri.parse('${APIConfig.baseUrl}/clients/$id'),
        headers: _getHeaders(),
        timeout: APIConfig.timeout,
      ).timeout(APIConfig.timeout);
      
      if (response.statusCode != 204) {
        throw Exception('Failed to delete client: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Delete client error: $e');
    }
  }
  
  // MARK: - Portraits
  
  Future<PortraitModel> uploadPortrait(
    String clientId,
    List<int> imageBytes,
    String fileName,
  ) async {
    try {
      final request = http.MultipartRequest(
        'POST',
        Uri.parse('${APIConfig.baseUrl}/portraits/'),
      )
        ..headers.addAll(_getHeaders())
        ..fields['client_id'] = clientId
        ..files.add(
          http.MultipartFile.fromBytes(
            'image',
            imageBytes,
            filename: fileName,
          ),
        );
      
      final response = await request.send().timeout(APIConfig.timeout);
      
      if (response.statusCode == 201) {
        final body = await response.stream.bytesToString();
        return PortraitModel.fromJson(jsonDecode(body));
      } else {
        throw Exception('Portrait upload failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Upload portrait error: $e');
    }
  }
}

// MARK: - Provider
class VertexARProvider extends ChangeNotifier {
  final VertexARService _service = VertexARService();
  
  List<ClientModel> _clients = [];
  bool _isLoading = false;
  String? _error;
  
  List<ClientModel> get clients => _clients;
  bool get isLoading => _isLoading;
  String? get error => _error;
  
  Future<void> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      await _service.login(username, password);
      await fetchClients();
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
  
  Future<void> fetchClients() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      final response = await _service.getClients();
      _clients = response.items;
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
  
  Future<void> createClient(String phone, String name) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      final newClient = await _service.createClient(phone, name);
      _clients.add(newClient);
    } catch (e) {
      _error = e.toString();
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}

// MARK: - UI
void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => VertexARProvider()),
      ],
      child: const MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);
  
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vertex AR',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: const LoginScreen(),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);
  
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  
  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Vertex AR Login')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Consumer<VertexARProvider>(
          builder: (context, provider, _) {
            return Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TextField(
                  controller: _usernameController,
                  decoration: const InputDecoration(
                    labelText: 'Username',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: provider.isLoading
                      ? null
                      : () async {
                    await provider.login(
                      _usernameController.text,
                      _passwordController.text,
                    );
                    
                    if (!context.mounted) return;
                    
                    if (provider.error == null) {
                      Navigator.of(context).pushReplacement(
                        MaterialPageRoute(
                          builder: (_) => const ClientsScreen(),
                        ),
                      );
                    }
                  },
                  child: provider.isLoading
                      ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(),
                  )
                      : const Text('Login'),
                ),
                if (provider.error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Text(
                      provider.error!,
                      style: const TextStyle(color: Colors.red),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class ClientsScreen extends StatefulWidget {
  const ClientsScreen({Key? key}) : super(key: key);
  
  @override
  State<ClientsScreen> createState() => _ClientsScreenState();
}

class _ClientsScreenState extends State<ClientsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<VertexARProvider>().fetchClients();
    });
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Clients'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () {
              _showNewClientDialog(context);
            },
          ),
        ],
      ),
      body: Consumer<VertexARProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          
          if (provider.error != null) {
            return Center(
              child: Text(
                'Error: ${provider.error}',
                style: const TextStyle(color: Colors.red),
              ),
            );
          }
          
          if (provider.clients.isEmpty) {
            return const Center(child: Text('No clients'));
          }
          
          return ListView.builder(
            itemCount: provider.clients.length,
            itemBuilder: (context, index) {
              final client = provider.clients[index];
              return ListTile(
                title: Text(client.name),
                subtitle: Text(client.phone),
                trailing: Text(
                  client.createdAt.split('T').first,
                  style: const TextStyle(fontSize: 12),
                ),
              );
            },
          );
        },
      ),
    );
  }
  
  void _showNewClientDialog(BuildContext context) {
    final phoneController = TextEditingController();
    final nameController = TextEditingController();
    
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('New Client'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: 'Name'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: phoneController,
              decoration: const InputDecoration(labelText: 'Phone'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: Navigator.of(context).pop,
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              await context.read<VertexARProvider>().createClient(
                phoneController.text,
                nameController.text,
              );
              if (context.mounted) Navigator.of(context).pop();
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }
}
```

---

## React Native (TypeScript)

### Полный пример приложения

```typescript
import React, { useState, useEffect, createContext, useContext } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  StyleSheet,
  Alert,
  SafeAreaView,
  ScrollView,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

// MARK: - Types
interface AuthToken {
  access_token: string;
  token_type: string;
}

interface Client {
  id: string;
  phone: string;
  name: string;
  created_at: string;
}

interface ClientsList {
  items: Client[];
  total: number;
  page: number;
  page_size: number;
}

interface Portrait {
  id: string;
  client_id: string;
  permanent_link: string;
  qr_code_base64?: string;
  image_path: string;
  view_count: number;
  created_at: string;
}

// MARK: - API Service
class VertexARAPI {
  private baseUrl = 'https://api.vertex-ar.com';
  private token: string | null = null;
  
  async init() {
    try {
      this.token = await SecureStore.getItemAsync('vertex_ar_token');
    } catch (error) {
      console.error('Failed to load token:', error);
    }
  }
  
  private async makeRequest(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<any> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
        timeout: 30000,
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      
      if (response.status === 204) {
        return null;
      }
      
      return await response.json();
    } catch (error) {
      throw error;
    }
  }
  
  async login(username: string, password: string): Promise<AuthToken> {
    const response = await this.makeRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    
    this.token = response.access_token;
    await SecureStore.setItemAsync('vertex_ar_token', response.access_token);
    
    return response;
  }
  
  async logout(): Promise<void> {
    await this.makeRequest('/auth/logout', { method: 'POST' });
    this.token = null;
    await SecureStore.deleteItemAsync('vertex_ar_token');
  }
  
  async createClient(phone: string, name: string): Promise<Client> {
    return this.makeRequest('/clients/', {
      method: 'POST',
      body: JSON.stringify({
        phone,
        name,
        company_id: 'vertex-ar-default',
      }),
    });
  }
  
  async getClients(page = 1, pageSize = 50): Promise<ClientsList> {
    return this.makeRequest(
      `/clients/?page=${page}&page_size=${pageSize}`,
      { method: 'GET' }
    );
  }
  
  async getClient(id: string): Promise<Client> {
    return this.makeRequest(`/clients/${id}`, { method: 'GET' });
  }
  
  async updateClient(
    id: string,
    updates: Partial<Client>
  ): Promise<Client> {
    return this.makeRequest(`/clients/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }
  
  async deleteClient(id: string): Promise<void> {
    return this.makeRequest(`/clients/${id}`, { method: 'DELETE' });
  }
  
  async uploadPortrait(
    clientId: string,
    imageUri: string
  ): Promise<Portrait> {
    const formData = new FormData();
    formData.append('client_id', clientId);
    formData.append('image', {
      uri: imageUri,
      type: 'image/jpeg',
      name: 'portrait.jpg',
    } as any);
    
    const url = `${this.baseUrl}/portraits/`;
    
    const headers: any = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });
    
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status}`);
    }
    
    return response.json();
  }
}

// MARK: - Context
interface AuthContextType {
  token: string | null;
  isLoading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const api = new VertexARAPI();
  
  useEffect(() => {
    api.init().then(() => {
      setIsLoading(false);
    });
  }, []);
  
  const login = async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.login(username, password);
      setToken(response.access_token);
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };
  
  const logout = async () => {
    setIsLoading(true);
    
    try {
      await api.logout();
      setToken(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <AuthContext.Provider value={{ token, isLoading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// MARK: - Screens
const LoginScreen: React.FC<{ onLoginSuccess: () => void }> = ({
  onLoginSuccess,
}) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  
  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) {
      Alert.alert('Error', 'Please enter username and password');
      return;
    }
    
    setIsLoading(true);
    try {
      await login(username, password);
      onLoginSuccess();
    } catch (error: any) {
      Alert.alert('Login Failed', error.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.content}>
        <Text style={styles.title}>Vertex AR</Text>
        
        <TextInput
          style={styles.input}
          placeholder="Username"
          value={username}
          onChangeText={setUsername}
          editable={!isLoading}
        />
        
        <TextInput
          style={styles.input}
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          editable={!isLoading}
        />
        
        <TouchableOpacity
          style={[styles.button, isLoading && styles.buttonDisabled]}
          onPress={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>Login</Text>
          )}
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const ClientsScreen: React.FC = () => {
  const [clients, setClients] = useState<Client[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [newName, setNewName] = useState('');
  const { logout } = useAuth();
  
  const api = new VertexARAPI();
  
  useEffect(() => {
    fetchClients();
  }, []);
  
  const fetchClients = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.getClients();
      setClients(response.items);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleCreateClient = async () => {
    if (!newPhone.trim() || !newName.trim()) {
      Alert.alert('Error', 'Please fill all fields');
      return;
    }
    
    try {
      const newClient = await api.createClient(newPhone, newName);
      setClients([...clients, newClient]);
      setNewPhone('');
      setNewName('');
      setShowNewForm(false);
    } catch (err: any) {
      Alert.alert('Error', err.message);
    }
  };
  
  const handleLogout = async () => {
    try {
      await logout();
    } catch (err: any) {
      Alert.alert('Error', err.message);
    }
  };
  
  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Clients</Text>
        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.logoutButton}>Logout</Text>
        </TouchableOpacity>
      </View>
      
      {/* Error Message */}
      {error && (
        <View style={styles.errorBox}>
          <Text style={styles.errorText}>{error}</Text>
          <TouchableOpacity onPress={fetchClients}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      )}
      
      {/* Loading */}
      {isLoading && !error ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
        </View>
      ) : null}
      
      {/* Clients List */}
      {!isLoading && clients.length > 0 ? (
        <FlatList
          data={clients}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={styles.clientCard}>
              <Text style={styles.clientName}>{item.name}</Text>
              <Text style={styles.clientPhone}>{item.phone}</Text>
              <Text style={styles.clientDate}>{item.created_at}</Text>
            </View>
          )}
          contentContainerStyle={styles.listContent}
        />
      ) : !isLoading ? (
        <View style={styles.centerContainer}>
          <Text>No clients found</Text>
        </View>
      ) : null}
      
      {/* Add Button */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => setShowNewForm(!showNewForm)}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>
      
      {/* New Client Form */}
      {showNewForm && (
        <View style={styles.formContainer}>
          <TextInput
            style={styles.input}
            placeholder="Phone"
            value={newPhone}
            onChangeText={setNewPhone}
          />
          <TextInput
            style={styles.input}
            placeholder="Name"
            value={newName}
            onChangeText={setNewName}
          />
          <TouchableOpacity
            style={styles.button}
            onPress={handleCreateClient}
          >
            <Text style={styles.buttonText}>Create</Text>
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
};

// MARK: - Main App
const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const { token } = useAuth();
  
  useEffect(() => {
    setIsLoggedIn(!!token);
  }, [token]);
  
  return isLoggedIn ? (
    <ClientsScreen />
  ) : (
    <LoginScreen onLoginSuccess={() => setIsLoggedIn(true)} />
  );
};

export default function VertexARApp() {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
}

// MARK: - Styles
const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    flex: 1,
    padding: 20,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    marginBottom: 30,
    textAlign: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#007AFF',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  logoutButton: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#ddd',
  },
  button: {
    backgroundColor: '#007AFF',
    borderRadius: 8,
    paddingVertical: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  errorBox: {
    backgroundColor: '#fee',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  errorText: {
    color: '#c33',
    fontSize: 14,
  },
  retryText: {
    color: '#007AFF',
    fontWeight: '600',
  },
  listContent: {
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  clientCard: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 16,
    marginBottom: 8,
  },
  clientName: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  clientPhone: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  clientDate: {
    fontSize: 12,
    color: '#999',
  },
  fab: {
    position: 'absolute',
    right: 16,
    bottom: 16,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#007AFF',
    justifyContent: 'center',
    alignItems: 'center',
  },
  fabText: {
    fontSize: 28,
    color: '#fff',
    fontWeight: 'bold',
  },
  formContainer: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
    padding: 16,
  },
});
```

---

## Web (TypeScript)

```typescript
import React, { useState, useCallback, useEffect } from 'react';
import axios, { AxiosInstance, AxiosError } from 'axios';

// MARK: - Types
interface AuthToken {
  access_token: string;
  token_type: string;
}

interface Client {
  id: string;
  phone: string;
  name: string;
  created_at: string;
}

interface Portrait {
  id: string;
  client_id: string;
  permanent_link: string;
  qr_code_base64?: string;
  image_path: string;
  view_count: number;
  created_at: string;
}

// MARK: - API Client
class VertexARWebClient {
  private api: AxiosInstance;
  private token: string | null = null;
  
  constructor(baseUrl = 'https://api.vertex-ar.com') {
    this.api = axios.create({
      baseURL: baseUrl,
      timeout: 30000,
    });
    
    this.api.interceptors.request.use((config) => {
      if (this.token) {
        config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });
    
    this.loadTokenFromLocalStorage();
  }
  
  private loadTokenFromLocalStorage() {
    this.token = localStorage.getItem('vertex_ar_token');
  }
  
  private saveTokenToLocalStorage(token: string) {
    localStorage.setItem('vertex_ar_token', token);
  }
  
  async login(username: string, password: string): Promise<AuthToken> {
    const response = await this.api.post<AuthToken>('/auth/login', {
      username,
      password,
    });
    
    this.token = response.data.access_token;
    this.saveTokenToLocalStorage(this.token);
    
    return response.data;
  }
  
  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
    this.token = null;
    localStorage.removeItem('vertex_ar_token');
  }
  
  async createClient(phone: string, name: string): Promise<Client> {
    const response = await this.api.post<Client>('/clients/', {
      phone,
      name,
      company_id: 'vertex-ar-default',
    });
    return response.data;
  }
  
  async getClients(page = 1, pageSize = 50) {
    const response = await this.api.get('/clients/', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  }
  
  async getClient(id: string): Promise<Client> {
    const response = await this.api.get<Client>(`/clients/${id}`);
    return response.data;
  }
  
  async updateClient(id: string, updates: Partial<Client>): Promise<Client> {
    const response = await this.api.put<Client>(`/clients/${id}`, updates);
    return response.data;
  }
  
  async deleteClient(id: string): Promise<void> {
    await this.api.delete(`/clients/${id}`);
  }
  
  async uploadPortrait(clientId: string, file: File): Promise<Portrait> {
    const formData = new FormData();
    formData.append('client_id', clientId);
    formData.append('image', file);
    
    const response = await this.api.post<Portrait>('/portraits/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  }
}

// MARK: - React Component
const ClientsApp: React.FC = () => {
  const [api] = useState(() => new VertexARWebClient());
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(!!localStorage.getItem('vertex_ar_token'));
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      await api.login(credentials.username, credentials.password);
      setIsLoggedIn(true);
      setCredentials({ username: '', password: '' });
      await fetchClients();
    } catch (err) {
      const axiosError = err as AxiosError;
      setError(
        axiosError.response?.data?.detail || 'Login failed'
      );
    } finally {
      setLoading(false);
    }
  };
  
  const fetchClients = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await api.getClients();
      setClients(data.items);
    } catch (err) {
      const axiosError = err as AxiosError;
      setError(
        axiosError.response?.data?.detail || 'Failed to fetch clients'
      );
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    if (isLoggedIn) {
      fetchClients();
    }
  }, [isLoggedIn]);
  
  const handleLogout = async () => {
    try {
      await api.logout();
      setIsLoggedIn(false);
      setClients([]);
    } catch (err) {
      setError('Logout failed');
    }
  };
  
  if (!isLoggedIn) {
    return (
      <div style={styles.container}>
        <div style={styles.form}>
          <h1>Vertex AR Login</h1>
          {error && <div style={styles.error}>{error}</div>}
          <form onSubmit={handleLogin}>
            <input
              type="text"
              placeholder="Username"
              value={credentials.username}
              onChange={(e) =>
                setCredentials({
                  ...credentials,
                  username: e.target.value,
                })
              }
              style={styles.input}
              disabled={loading}
            />
            <input
              type="password"
              placeholder="Password"
              value={credentials.password}
              onChange={(e) =>
                setCredentials({
                  ...credentials,
                  password: e.target.value,
                })
              }
              style={styles.input}
              disabled={loading}
            />
            <button type="submit" style={styles.button} disabled={loading}>
              {loading ? 'Loading...' : 'Login'}
            </button>
          </form>
        </div>
      </div>
    );
  }
  
  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>Clients</h1>
        <button onClick={handleLogout} style={styles.logoutButton}>
          Logout
        </button>
      </header>
      
      {error && <div style={styles.error}>{error}</div>}
      
      {loading && <div style={styles.loading}>Loading...</div>}
      
      <table style={styles.table}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Phone</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {clients.map((client) => (
            <tr key={client.id}>
              <td>{client.name}</td>
              <td>{client.phone}</td>
              <td>{new Date(client.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'Arial, sans-serif',
  },
  form: {
    maxWidth: '400px',
    margin: '50px auto',
    padding: '20px',
    border: '1px solid #ddd',
    borderRadius: '8px',
  },
  input: {
    width: '100%',
    padding: '10px',
    marginBottom: '10px',
    border: '1px solid #ddd',
    borderRadius: '4px',
  },
  button: {
    width: '100%',
    padding: '10px',
    backgroundColor: '#007AFF',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '16px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '20px',
    borderBottom: '1px solid #ddd',
    paddingBottom: '10px',
  },
  logoutButton: {
    padding: '8px 16px',
    backgroundColor: '#dc3545',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  error: {
    backgroundColor: '#fee',
    color: '#c33',
    padding: '10px',
    borderRadius: '4px',
    marginBottom: '10px',
  },
  loading: {
    textAlign: 'center',
    padding: '20px',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '20px',
  },
};

export default ClientsApp;
```

---

**Все примеры готовы к использованию и тестированию.**

Последнее обновление: 2024
