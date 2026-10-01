import StoreKit
import Observation

/// StoreKit 2. Free tier: unlimited system voices + every accessibility feature.
/// Plus: cloud voices (metered, meter always visible) + unlimited summaries.
/// Monthly and annual only. No weekly plans, no paywall before the first listen.
@Observable
@MainActor
final class Store {
    static let productIDs = ["com.theoryofweb.narrata.plus.monthly", "com.theoryofweb.narrata.plus.annual"]

    private(set) var products: [Product] = []
    private(set) var hasPlus = false
    /// Cloud-voice characters used this billing period; shown in Settings and the voice picker.
    var cloudCharactersUsed = 0
    let cloudCharacterAllowance = 2_000_000   // ≈ 37 listening hours

    func load() async {
        products = (try? await Product.products(for: Self.productIDs)) ?? []
        await refreshEntitlements()
        Task.detached { [weak self] in
            for await result in Transaction.updates {
                if case .verified(let t) = result { await t.finish() }
                await self?.refreshEntitlements()
            }
        }
    }

    func purchase(_ product: Product) async throws {
        let result = try await product.purchase()
        if case .success(.verified(let t)) = result { await t.finish() }
        await refreshEntitlements()
    }

    func refreshEntitlements() async {
        var active = false
        for await result in Transaction.currentEntitlements {
            if case .verified(let t) = result, Self.productIDs.contains(t.productID), t.revocationDate == nil { active = true }
        }
        hasPlus = active
    }
}
