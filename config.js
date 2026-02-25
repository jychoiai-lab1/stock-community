const SUPABASE_URL = 'https://miyrssfrjvhwswjylahw.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMjIxNDYsImV4cCI6MjA4NzU5ODE0Nn0.oBwDXc1x4II1M4NX5AcfXIt2MTx4L3m4e9mHwqo-ObA';
const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
