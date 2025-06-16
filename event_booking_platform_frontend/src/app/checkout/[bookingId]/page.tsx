'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { loadStripe, StripeElementsOptions } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import Link from 'next/link'; // Added import
import CheckoutForm from '@/components/payments/CheckoutForm';
import PaymentService from '@/services/PaymentService';
import { useAuth } from '@/contexts/AuthContext';
import LoadingSpinner from '@/components/common/LoadingSpinner'; // Import common components
import AlertMessage from '@/components/common/AlertMessage';   // Import common components
import bookingService from '@/services/bookingService'; // For fetching actual booking details

// Make sure to call `loadStripe` outside of a component’s render to avoid
// recreating the `Stripe` object on every render.
// Ensure your Stripe publishable key is an environment variable
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "your_default_publishable_key");

// Interface for actual Booking details fetched from backend
interface FullBookingDetails {
  id: string;
  event_details?: { // Assuming event_details is nested from your BookingSerializer
    name: string;
    start_time: string;
    ticket_price: string; // Assuming string from backend
  };
  number_of_tickets: number;
  total_price: string; // Assuming string from backend
  price_per_ticket_at_booking?: string; // Added this field
  status: string;
  // Add other fields you might need from the Booking model
}


const CheckoutPage = () => {
  const params = useParams();
  const bookingId = params.bookingId as string;

  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [bookingDetails, setBookingDetails] = useState<FullBookingDetails | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user, isLoading: authLoading } = useAuth();

  useEffect(() => {
    if (authLoading) return; // Wait for auth state to resolve

    if (!user) {
      setError("Please log in to make a payment.");
      setLoading(false);
      return;
    }
    if (!bookingId) {
      setError("Booking ID is missing.");
      setLoading(false);
      return;
    }

    const initializeCheckout = async () => {
      setLoading(true);
      setError(null);
      try {
        // 1. Fetch full booking details from your backend
        const fetchedBooking = await bookingService.getBookingById(bookingId);
        setBookingDetails(fetchedBooking);

        if (fetchedBooking.status !== 'pending_payment') { // Changed 'pending' to 'pending_payment'
            setError(`This booking is already ${fetchedBooking.status} and cannot be paid for. Payment can only be made for 'pending_payment' bookings.`);
            setLoading(false);
            return;
        }

        // 2. Create Payment Intent
        const paymentIntentResponse = await PaymentService.createPaymentIntent({ booking_id: bookingId });

        if (paymentIntentResponse.client_secret && paymentIntentResponse.payment_id) {
          setClientSecret(paymentIntentResponse.client_secret);
          setPaymentId(paymentIntentResponse.payment_id);
        } else {
          setError(paymentIntentResponse.error || 'Failed to initialize payment gateway.');
        }
      } catch (err: any) {
        console.error('Error initializing checkout:', err);
        setError(err.response?.data?.detail || err.message || 'An unexpected error occurred during checkout initialization.');
      } finally {
        setLoading(false);
      }
    };

    initializeCheckout();
  }, [bookingId, user, authLoading]);

  const options: StripeElementsOptions | undefined = clientSecret ? {
    clientSecret,
    appearance: { theme: 'stripe' /* or 'night', 'flat' */ }
  } : undefined;

  if (authLoading || (loading && !bookingDetails && !error)) { // Show main loader if auth or initial data is loading
    return <LoadingSpinner message="Loading checkout..." />;
  }

  if (error) {
    return (
      <div className="container mx-auto p-4 text-center">
        <AlertMessage message={error} type="error" />
        <Link href="/dashboard" className="link-primary mt-4 inline-block">Go to Dashboard</Link>
      </div>
    );
  }

  if (!clientSecret || !options || !paymentId) {
    return (
        <div className="container mx-auto p-4 text-center">
            <AlertMessage message="Could not initialize payment gateway. Required information is missing." type="error" />
             <Link href="/dashboard" className="link-primary mt-4 inline-block">Go to Dashboard</Link>
        </div>
    );
  }

  if (!bookingDetails) {
      // This case should ideally be covered by the error state if fetching bookingDetails fails
      return <LoadingSpinner message="Loading booking information..." />;
  }

  return (
    <div className="container mx-auto p-4 max-w-2xl">
      <header className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-gray-800 dark:text-white">Checkout</h1>
      </header>

      <div className="mb-6 p-6 bg-white dark:bg-gray-800 shadow-md rounded-lg">
        <h2 className="text-xl font-semibold text-gray-700 dark:text-white mb-4">Booking Summary</h2>
        <div className="space-y-2">
            <p><span className="font-semibold">Event:</span> {bookingDetails.event_details?.name || 'N/A'}</p>
            <p><span className="font-semibold">Tickets:</span> {bookingDetails.number_of_tickets}</p>
            {bookingDetails.price_per_ticket_at_booking && ( // Conditional rendering
              <p><span className="font-semibold">Price per Ticket:</span> ${parseFloat(bookingDetails.price_per_ticket_at_booking).toFixed(2)}</p>
            )}
            <p className="text-lg font-bold"><span className="font-semibold">Total Amount:</span> ${parseFloat(bookingDetails.total_price).toFixed(2)}</p>
            <p><span className="font-semibold">Booking ID:</span> {bookingDetails.id}</p>
            <p><span className="font-semibold">Status:</span> <span className="font-medium capitalize">{bookingDetails.status}</span></p>
        </div>
      </div>

      <Elements stripe={stripePromise} options={options}>
        <CheckoutForm bookingId={bookingId} paymentId={paymentId} />
      </Elements>
    </div>
  );
};

export default CheckoutPage;
