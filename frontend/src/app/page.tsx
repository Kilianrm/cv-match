import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function Home() {
  const cookieStore = await cookies();
  const authToken = cookieStore.get("cv_access_token");

  // Redirect authenticated users to dashboard
  if (authToken) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <nav className="border-b border-primary/10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold text-foreground">CV Match</h2>
          <a href="/api/auth/login">
            <button className="px-6 py-2 bg-primary text-background rounded-lg font-semibold hover:bg-primary/90 transition-colors">
              Login
            </button>
          </a>
        </div>
      </nav>

      {/* Hero */}
      <div className="flex-1 flex items-center justify-center px-6 py-20">
        <div className="text-center max-w-3xl">
          <h1 className="text-5xl md:text-6xl font-bold text-foreground mb-6">
            Find Your Perfect Job Match
          </h1>
          <p className="text-xl text-muted mb-8">
            Upload your CV and discover job opportunities tailored to your skills and experience.
            Get AI-powered suggestions to optimize your applications and land your next role.
          </p>

          <a href="/api/auth/login">
            <button className="px-8 py-4 bg-primary text-background rounded-lg font-bold text-lg hover:bg-primary/90 transition-colors inline-block">
              Get Started Free
            </button>
          </a>

          <p className="text-sm text-muted mt-6">No credit card required. Start matching today.</p>
        </div>
      </div>

      {/* Features */}
      <div className="bg-surface border-t border-primary/10">
        <div className="max-w-7xl mx-auto px-6 py-20">
          <h2 className="text-3xl font-bold text-foreground text-center mb-12">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">??</span>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">1. Upload CV</h3>
              <p className="text-muted">
                Submit your CV in PDF or DOCX format and let our AI parse your profile automatically.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">??</span>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">2. Get Matches</h3>
              <p className="text-muted">
                Discover jobs that match your skills and experience. See your match score for each opportunity.
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">?</span>
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">3. Optimize</h3>
              <p className="text-muted">
                Get AI-powered suggestions to tailor your CV for each job opportunity you're interested in.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Benefits */}
      <div className="bg-foreground text-background py-20">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center mb-12">Why CV Match?</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                <span className="text-background font-bold">?</span>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Smart Matching</h3>
                <p className="opacity-90">AI-powered algorithm finds the best job fits for your profile</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                <span className="text-background font-bold">?</span>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Daily Digest</h3>
                <p className="opacity-90">Receive curated job recommendations delivered to your email</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                <span className="text-background font-bold">?</span>
              </div>
              <div>
                <h3 className="font-semibold mb-2">CV Optimization</h3>
                <p className="opacity-90">Get specific suggestions to improve your match score</p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                <span className="text-background font-bold">?</span>
              </div>
              <div>
                <h3 className="font-semibold mb-2">One-Time Setup</h3>
                <p className="opacity-90">Upload once and start matching immediately</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="bg-surface border-t border-primary/10 py-16">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">Ready to Find Your Match?</h2>
          <p className="text-muted mb-8">
            Join hundreds of job seekers using CV Match to land their ideal roles.
          </p>
          <a href="/api/auth/login">
            <button className="px-8 py-4 bg-primary text-background rounded-lg font-bold text-lg hover:bg-primary/90 transition-colors inline-block">
              Start Matching Now
            </button>
          </a>
        </div>
      </div>
    </div>
  );
}
