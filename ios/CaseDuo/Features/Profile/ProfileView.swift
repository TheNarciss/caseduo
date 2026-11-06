import CaseDuoCore
import SwiftUI

/// Profil: the daily goal ("Je m'engage"), notifications, sounds, time zone, the career story
/// the fit grader checks answers against, badges, and the account.
struct ProfileView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.palette) private var palette
    @State private var displayName = ""
    @State private var confirmDelete = false
    @State private var deleting = false
    @State private var showCommitment = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Form {
                if let me = model.me {
                    Section {
                        HStack(spacing: 14) {
                            Circle().fill(palette.accent).frame(width: 48, height: 48)
                                .overlay(Text(String((me.displayName ?? me.email).prefix(1)).uppercased())
                                    .font(.title3.weight(.heavy)).foregroundStyle(.black))
                            VStack(alignment: .leading, spacing: 2) {
                                Text(me.displayName ?? "Sans nom").font(.headline)
                                Text(me.email).font(.caption).foregroundStyle(Brand.textSecondary)
                            }
                            Spacer()
                            VStack(alignment: .trailing) {
                                Text(Format.xp(me.xpTotal)).font(.headline.monospacedDigit())
                                Text("record \(Format.streakDays(me.streakLongest))").font(.caption).foregroundStyle(Brand.textSecondary)
                            }
                        }
                        TextField("Prénom affiché", text: $displayName)
                            .onSubmit { Task { await model.update(MePatch(displayName: displayName)) } }
                    }

                    Section {
                        if let c = model.commitment, c.isActive {
                            LabeledContent("Objectif", value: "\(c.dailyXp) XP par jour")
                            LabeledContent("Jusqu'au", value: Format.shortDay(c.endDate))
                            LabeledContent("Tenu", value: "\(c.daysHeld) jour\(c.daysHeld > 1 ? "s" : "") sur \(c.dayIndex)")
                            Label("Verrouillé jusqu'au dernier jour : c'est ça, s'engager.", systemImage: "lock.fill")
                                .font(.footnote).foregroundStyle(Brand.textSecondary)
                        } else {
                            LabeledContent("Objectif", value: "\(me.dailyGoalXp) XP par jour")
                            if let c = model.commitment, c.isEnded {
                                Text(c.kept == true
                                     ? "Dernier engagement tenu : \(c.days) jours sans faute."
                                     : "Dernier engagement : \(c.daysHeld) jours tenus sur \(c.days).")
                                    .font(.footnote).foregroundStyle(Brand.textSecondary)
                            }
                            Button("Je m'engage") { showCommitment = true }
                                .buttonStyle(.pill)
                                .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
                        }
                    } header: {
                        Text("Engagement")
                    } footer: {
                        Text("L'objectif ne se change qu'en prenant un nouvel engagement : 7, 14 ou 30 jours, verrouillé.")
                    }

                    Section("Rappels et sons") {
                        Toggle("Notifications", isOn: Binding(
                            get: { me.notificationsEnabled },
                            set: { value in Task { await model.update(MePatch(notificationsEnabled: value)) } }))
                        Toggle("Sons", isOn: Binding(
                            get: { me.soundsEnabled },
                            set: { value in Task { await model.update(MePatch(soundsEnabled: value)) } }))
                        Picker("Fuseau horaire", selection: Binding(
                            get: { me.timezone },
                            set: { value in Task { await model.update(MePatch(timezone: value)) } })) {
                            ForEach(Self.timezones(including: me.timezone), id: \.self) { zone in
                                Text(Self.label(for: zone)).tag(zone)
                            }
                        }
                        Text("Un seul rappel par jour au maximum, à 20 h si l'objectif n'est pas atteint.")
                            .font(.footnote).foregroundStyle(Brand.textSecondary)
                    }

                    Section("Entretiens de fit") {
                        NavigationLink {
                            StoryEditorView()
                        } label: {
                            Label("Mon récit de parcours", systemImage: "person.text.rectangle")
                        }
                        Text(me.storyText?.isEmpty == false
                             ? "Le correcteur vérifie que tes réponses de fit restent cohérentes avec ce récit."
                             : "À remplir une fois : écoles, Thales Rungis, Thales Singapour, projets, pourquoi le conseil.")
                            .font(.footnote).foregroundStyle(Brand.textSecondary)
                    }

                    Section("Récompenses") {
                        NavigationLink {
                            BadgesView()
                        } label: {
                            Label("Badges", systemImage: "rosette")
                        }
                    }

                    if model.isAdmin {
                        Section("Admin") {
                            if let date = model.today?.date,
                               let url = URL(string: "\(AppConfig.siteURL.absoluteString)/admin/review/\(date)") {
                                Link(destination: url) {
                                    Label("Relire les exercices du jour", systemImage: "checklist")
                                }
                            }
                        }
                    }

                    Section {
                        Button("Se déconnecter") { Task { await model.signOut() } }
                        Button("Supprimer mon compte", role: .destructive) { confirmDelete = true }
                            .disabled(deleting)
                    } footer: {
                        Text("CaseDuo \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "")")
                    }

                    if let error { Section { ErrorBanner(message: error) } }
                } else {
                    LoadingView()
                }
            }
            .scrollContentBackground(.hidden)
            .background(Brand.background)
            .navigationTitle("Profil")
            .onAppear { displayName = model.me?.displayName ?? "" }
            .sheet(isPresented: $showCommitment) {
                CommitmentSheet()
                    .environment(model)
                    .environment(\.palette, model.palette)
            }
            .confirmationDialog("Supprimer ton compte ?", isPresented: $confirmDelete, titleVisibility: .visible) {
                Button("Supprimer définitivement", role: .destructive) { Task { await deleteAccount() } }
                Button("Annuler", role: .cancel) {}
            } message: {
                Text("Ta série, tes corrections, ton récit et ta ligue seront effacés. C'est irréversible.")
            }
        }
    }

    private func deleteAccount() async {
        deleting = true
        defer { deleting = false }
        do { try await model.deleteAccount() } catch { self.error = error.localizedDescription }
    }

    static func timezones(including current: String) -> [String] {
        var zones = ["Asia/Singapore", "Europe/Paris", "Europe/London", "America/New_York", "Asia/Hong_Kong",
                     "Asia/Tokyo", "Asia/Dubai", "Australia/Sydney"]
        for extra in [current, TimeZone.current.identifier] where !zones.contains(extra) { zones.append(extra) }
        return zones
    }

    static func label(for identifier: String) -> String {
        let city = identifier.split(separator: "/").last.map { $0.replacingOccurrences(of: "_", with: " ") } ?? identifier
        guard let zone = TimeZone(identifier: identifier) else { return city }
        let hours = Double(zone.secondsFromGMT()) / 3600
        let offset = hours == hours.rounded() ? String(format: "%+.0f", hours) : String(format: "%+.1f", hours)
        return "\(city) (UTC\(offset))"
    }
}

/// The career story, written once, sent to the fit grader with every fit answer.
struct StoryEditorView: View {
    @Environment(AppModel.self) private var model
    @Environment(\.dismiss) private var dismiss
    @State private var text = ""
    @State private var saving = false
    @State private var error: String?

    var body: some View {
        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 8) {
                Text("Écoles, Thales Rungis, Thales Singapour, projets marquants, pourquoi le conseil, pourquoi partir. Avec des chiffres.")
                    .font(.subheadline)
                    .foregroundStyle(Brand.textSecondary)
                if let error { ErrorBanner(message: error) }
            }
            .padding(16)
            TextEditor(text: $text)
                .scrollContentBackground(.hidden)
                .padding(12)
                .background(Brand.card)
            BottomActions {
                Text("\(text.count) caractères").font(.caption).foregroundStyle(Brand.textTertiary)
                Button {
                    Task { await save() }
                } label: {
                    if saving { ProgressView().tint(.black) } else { Text("Enregistrer") }
                }
                .buttonStyle(.pill)
                .disabled(saving || text == (model.me?.storyText ?? ""))
            }
        }
        .background(Brand.background)
        .navigationTitle("Mon récit")
        .navigationBarTitleDisplayMode(.inline)
        .onAppear { text = model.me?.storyText ?? "" }
    }

    private func save() async {
        saving = true
        defer { saving = false }
        do {
            try await model.saveStory(text)
            dismiss()
        } catch {
            model.handle(error)
            self.error = error.localizedDescription
        }
    }
}
