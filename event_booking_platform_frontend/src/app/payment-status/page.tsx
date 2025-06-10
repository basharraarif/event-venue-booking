'use client';

import React, { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useStripe } from '@stripe/react-stripe-js'; // Optional: if you need to retrieve PaymentIntent directly via Stripe.js
import PaymentService from '@/services/PaymentService'; // To fetch payment status from your backend
import Link from 'next/link';

const PaymentStatusPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const stripe = useStripe(); // Optional

  const paymentIntentClientSecret = searchParams.get('payment_intent_client_secret');
  const paymentIntentId = searchParams.get('payment_intent');
  const redirectStatus = searchParams.get('redirect_status');

  // Get custom params we passed in the return_url
  const localPaymentId = searchParams.get('payment_id');
  const bookingId = searchParams.get('booking_id');

  const [status, setStatus] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!stripe && !localPaymentId) { // If not using stripe object directly, localPaymentId is crucial
      // Stripe.js hasn't loaded yet, or localPaymentId is missing.
      // If you're not using `stripe.retrievePaymentIntent`, you might not need to wait for `stripe`.
      // For now, we'll primarily rely on our backend via localPaymentId.
      // If localPaymentId is also missing, we can't do much.
      if(!localPaymentId) {
        setMessage("Required payment information is missing from the URL.");
        setLoading(false);
      }
      // If stripe is needed and not loaded, you might want to show a loader or retry.
      // For this example, we proceed if localPaymentId is present.
      return;
    }

    setLoading(true);

    // Option 1: Retrieve PaymentIntent status using Stripe.js (requires client_secret)
    // This provides the most up-to-date status directly from Stripe.
    const retrieveWithStripeJS = async () => {
        if (stripe && paymentIntentClientSecret) {
            const { paymentIntent: pi } = await stripe.retrievePaymentIntent(paymentIntentClientSecret);
            if (pi) {
                setStatus(pi.status);
                switch (pi.status) {
                    case 'succeeded':
                        setMessage('Payment successful! Your booking is confirmed.');
                        break;
                    case 'processing':
                        setMessage('Payment processing. We will update you when payment is received.');
                        break;
                    case 'requires_payment_method':
                        setMessage('Payment failed. Please try another payment method.');
                        // router.push(`/checkout/${bookingId}`); // Redirect back to checkout
                        break;
                    default:
                        setMessage('Something went wrong with your payment. Please contact support.');
                        break;
                }
            } else {
                 setMessage('Could not retrieve payment intent details from Stripe.');
            }
        } else if (localPaymentId) {
            // Option 2: Fallback or primary method - Fetch status from your backend
            // This is useful if client_secret is not available or you want to rely on your server's record.
            try {
                const paymentDetails = await PaymentService.getPaymentDetails(localPaymentId);
                setStatus(paymentDetails.status);
                if (paymentDetails.status === 'succeeded') {
                    setMessage('Payment successful! Your booking is confirmed.');
                } else if (paymentDetails.status === 'pending' || paymentDetails.status === 'requires_action') {
                    setMessage('Your payment is pending. We will update you shortly.');
                } else if (paymentDetails.status === 'failed') {
                    setMessage('Payment failed. Please try again or contact support.');
                    // router.push(`/checkout/${bookingId}`); // Redirect back to checkout
                } else {
                    setMessage(`Payment status: ${paymentDetails.status}.`);
                }
            } catch (error) {
                console.error("Error fetching payment status from backend:", error);
                setMessage('Could not retrieve payment status from our server.');
            }
        } else {
            setMessage("Cannot determine payment status. Necessary identifiers are missing.");
        }
        setLoading(false);
    };

    retrieveWithStripeJS();

  }, [stripe, paymentIntentClientSecret, localPaymentId, router, bookingId]);


  if (loading) {
    return <div>Loading payment status...</div>;
  }

  return (
    <div className="container mx-auto p-4 text-center">
      <h1 className="text-2xl font-bold mb-4">Payment Status</h1>
      {message && <p className="mb-4">{message}</p>}
      {status === 'succeeded' && bookingId && (
        <Link href={`/bookings/${bookingId}/confirmation`} legacyBehavior>
          <a className="text-blue-500 hover:underline">View Booking Confirmation</a>
        </Link>
      )}
      {status !== 'succeeded' && bookingId && (
         <Link href={`/checkout/${bookingId}`} legacyBehavior>
          <a className="text-blue-500 hover:underline mr-2">Try Again</a>
        </Link>
      )}
       <Link href="/" legacyBehavior>
          <a className="text-blue-500 hover:underline">Go to Homepage</a>
        </Link>
    </div>
  );
};


// Wrap with Elements provider if you intend to use useStripe() for retrieving PI
// Otherwise, if only fetching from backend, it's not strictly needed here.
// For this example, as we might use useStripe(), we wrap it.
const PaymentStatusPageWrapper = () => {
  const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || "your_default_publishable_key_here");
  return (
    <Elements stripe={stripePromise}>
      <PaymentStatusPage />
    </Elements>
  );
}

export default PaymentStatusPageWrapper;
