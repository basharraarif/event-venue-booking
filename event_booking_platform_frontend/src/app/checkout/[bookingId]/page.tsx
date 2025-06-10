'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { loadStripe, StripeElementsOptions } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import CheckoutForm from '@/components/payments/CheckoutForm'; // Adjust path if needed
import PaymentService from '@/services/PaymentService'; // Adjust path if needed
import { useAuth } from '@/contexts/AuthContext'; // Assuming you have an AuthContext

// Make sure to call `loadStripe` outside of a component’s render to avoid
// recreating the `Stripe` object on every render.
// Ensure your Stripe publishable key is an environment variable
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "your_default_publishable_key");

interface BookingDetails {
  id: string;
  event_name: string;
  total_price: number;
  currency_code: string;
  // Add other relevant booking details you might want to display
}

const CheckoutPage = () => {
  const params = useParams();
  const bookingId = params.bookingId as string;
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentId, setPaymentId] = useState<string | null>(null);
  const [bookingDetails, setBookingDetails] = useState<BookingDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user } = useAuth(); // Get authenticated user

  useEffect(() => {
    if (!bookingId || !user) {
      // If there's no bookingId or user, don't attempt to fetch
      if(!user) setError("Please log in to make a payment.");
      setLoading(false);
      return;
    }

    const fetchPaymentIntentAndBooking = async () => {
      setLoading(true);
      setError(null);
      try {
        // TODO: Fetch booking details first to display amount, etc.
        // This is a placeholder - you'll need an actual endpoint and service method
        // For now, let's assume a mock booking detail fetch or pass it via state
        // const fetchedBooking = await BookingService.getBookingDetails(bookingId);
        // setBookingDetails(fetchedBooking);

        // For now, using placeholder booking details.
        // In a real app, fetch this from your backend using bookingId.
        // Ensure the backend endpoint for booking details exists and is called here.
        // For example: const bookingData = await BookingService.getBooking(bookingId);
        // setBookingDetails(bookingData);
        // const amountToPay = bookingData.total_price; // This should come from your backend

        // Create Payment Intent
        const paymentIntentResponse = await PaymentService.createPaymentIntent({ booking_id: bookingId });

        if (paymentIntentResponse.client_secret && paymentIntentResponse.payment_id) {
          setClientSecret(paymentIntentResponse.client_secret);
          setPaymentId(paymentIntentResponse.payment_id);
          // Mock booking details until a proper service is implemented
          setBookingDetails({
            id: bookingId,
            event_name: "Placeholder Event Name", // Replace with actual data
            total_price: 0, // Replace with actual data from booking
            currency_code: "USD" // Replace with actual data
          });
        } else {
          setError(paymentIntentResponse.error || 'Failed to initialize payment.');
        }
      } catch (err: any) {
        console.error('Error in checkout page:', err);
        setError(err.message || 'An unexpected error occurred.');
      } finally {
        setLoading(false);
      }
    };

    fetchPaymentIntentAndBooking();
  }, [bookingId, user]);

  const options: StripeElementsOptions | undefined = clientSecret ? { clientSecret } : undefined;

  if (loading) {
    return <div>Loading checkout...</div>;
  }

  if (error) {
    return <div style={{ color: 'red' }}>Error: {error}</div>;
  }

  if (!clientSecret || !options) {
    return <div>Could not initialize payment. Client secret is missing.</div>;
  }

  if (!bookingDetails) {
      return <div>Loading booking details... (or booking not found)</div>;
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Checkout</h1>
      <div className="mb-4">
        <h2 className="text-xl">Booking Summary</h2>
        <p>Booking ID: {bookingDetails.id}</p>
        {/* <p>Event: {bookingDetails.event_name}</p> */}
        {/* <p>Amount: {bookingDetails.total_price} {bookingDetails.currency_code.toUpperCase()}</p> */}
        <p>Please enter your payment details below.</p>
      </div>
      <Elements stripe={stripePromise} options={options}>
        <CheckoutForm bookingId={bookingId} paymentId={paymentId!} />
      </Elements>
    </div>
  );
};

export default CheckoutPage;
