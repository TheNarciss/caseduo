import AuthenticationServices
import CryptoKit
import SwiftUI

/// Same sign-in as Tangent: e-mail and password, or Sign in with Apple natively (the id_token
/// goes to `/auth/apple/native`). The session is a cookie. No sign-up form: the account exists
/// (CLI) or Apple creates it.
struct LoginView: View {
    @Environment(AppModel.self) private var model
    @State private var email = ""
    @State private var password = ""
    @State private var busy = false
    @State private var error: String?
    @State private var nonce = ""
    @FocusState private var focus: Field?

    enum Field { case email, password }

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 22) {
                    VStack(alignment: .leading, spacing: 10) {
                        FlameView(streak: 0, lit: true, size: 64)
                        Text("CaseDuo").font(.largeTitle.weight(.heavy))
                        Text("Cinq cases et des brainteasers par jour. Une série à tenir.")
                            .font(.title3)
                            .foregroundStyle(Brand.textSecondary)
                    }
                    .padding(.top, 40)

                    VStack(spacing: 12) {
                        TextField("E-mail", text: $email)
                            .textContentType(.username)
                            .keyboardType(.emailAddress)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .focused($focus, equals: .email)
                            .submitLabel(.next)
                            .onSubmit { focus = .password }
                            .padding(16)
                            .card(radius: 16)
                        SecureField("Mot de passe", text: $password)
                            .textContentType(.password)
                            .focused($focus, equals: .password)
                            .submitLabel(.go)
                            .onSubmit { Task { await signIn() } }
                            .padding(16)
                            .card(radius: 16)
                    }

                    if let error { ErrorBanner(message: error) { self.error = nil } }
                }
                .padding(.horizontal, 24)
            }
            .scrollDismissesKeyboard(.interactively)

            BottomActions {
                Button {
                    Task { await signIn() }
                } label: {
                    if busy { ProgressView().tint(.black) } else { Text("Se connecter") }
                }
                .buttonStyle(.pill)
                .disabled(busy || email.isEmpty || password.isEmpty)

                if model.providers.apple {
                    SignInWithAppleButton(.signIn) { request in
                        nonce = Self.randomNonce()
                        request.requestedScopes = [.fullName, .email]
                        request.nonce = Self.sha256(nonce)
                    } onCompletion: { result in
                        Task { await handleApple(result) }
                    }
                    .signInWithAppleButtonStyle(.white)
                    .frame(height: 52)
                    .clipShape(Capsule())
                    .disabled(busy)
                }
            }
        }
    }

    private func signIn() async {
        guard !email.isEmpty, !password.isEmpty else { return }
        busy = true
        defer { busy = false }
        do {
            try await model.signIn(email: email.trimmingCharacters(in: .whitespaces), password: password)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func handleApple(_ result: Result<ASAuthorization, Error>) async {
        switch result {
        case .failure(let failure):
            if (failure as? ASAuthorizationError)?.code != .canceled {
                error = "Connexion Apple impossible : \(failure.localizedDescription)"
            }
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                  let tokenData = credential.identityToken,
                  let token = String(data: tokenData, encoding: .utf8) else {
                error = "Apple n'a pas renvoyé de jeton."
                return
            }
            let name = credential.fullName.flatMap { PersonNameComponentsFormatter().string(from: $0) }
            busy = true
            defer { busy = false }
            do {
                try await model.signInWithApple(identityToken: token, nonce: nonce,
                                                displayName: (name?.isEmpty ?? true) ? nil : name)
            } catch {
                self.error = error.localizedDescription
            }
        }
    }

    /// A random string kept by the app; Apple receives its SHA-256 and puts it in the token.
    static func randomNonce(length: Int = 32) -> String {
        let charset = Array("0123456789ABCDEFGHIJKLMNOPQRSTUVXYZabcdefghijklmnopqrstuvwxyz-._")
        var generator = SystemRandomNumberGenerator()
        return String((0..<length).map { _ in charset.randomElement(using: &generator)! })
    }

    static func sha256(_ input: String) -> String {
        SHA256.hash(data: Data(input.utf8)).map { String(format: "%02x", $0) }.joined()
    }
}
