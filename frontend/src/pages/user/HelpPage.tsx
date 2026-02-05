import React from 'react';
import {
  QuestionMarkCircleIcon,
  BookOpenIcon,
  ChatBubbleLeftRightIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline';
import { Card, CardHeader, Button } from '../../components/ui';

const faqs = [
  {
    question: 'How do I update my profile information?',
    answer:
      'Navigate to the Profile page using the sidebar menu. You can update your display name, email, affiliation, and prefix. Click "Save Changes" when you\'re done.',
  },
  {
    question: 'What are roles and permissions?',
    answer:
      'Roles determine what features and data you can access within the Atlas platform. They are assigned by administrators and synced with the WebAPI security system.',
  },
  {
    question: 'How do I change my password?',
    answer:
      'Go to the "Change Password" page from the sidebar. Enter your current password and your new password twice for confirmation.',
  },
  {
    question: 'Why is my account disabled?',
    answer:
      'If your account is disabled, please contact an administrator. Account disabling may occur due to security reasons or administrative actions.',
  },
  {
    question: 'How can I request additional permissions?',
    answer:
      'Contact your administrator with details about the permissions you need and the reason for the request. They will review and grant appropriate access.',
  },
];

export const HelpPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
          Help & Support
        </h1>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Find answers to common questions and get support
        </p>
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card hover className="text-center">
          <div className="flex flex-col items-center">
            <div className="p-3 rounded-full bg-brand-100 dark:bg-brand-900/30 mb-3">
              <BookOpenIcon className="h-6 w-6 text-brand-600 dark:text-brand-400" />
            </div>
            <h3 className="font-medium text-slate-900 dark:text-slate-100">
              Documentation
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Read the user guide
            </p>
          </div>
        </Card>

        <Card hover className="text-center">
          <div className="flex flex-col items-center">
            <div className="p-3 rounded-full bg-emerald-100 dark:bg-emerald-900/30 mb-3">
              <ChatBubbleLeftRightIcon className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h3 className="font-medium text-slate-900 dark:text-slate-100">
              Community
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Join the discussion
            </p>
          </div>
        </Card>

        <Card hover className="text-center">
          <div className="flex flex-col items-center">
            <div className="p-3 rounded-full bg-amber-100 dark:bg-amber-900/30 mb-3">
              <EnvelopeIcon className="h-6 w-6 text-amber-600 dark:text-amber-400" />
            </div>
            <h3 className="font-medium text-slate-900 dark:text-slate-100">
              Contact Support
            </h3>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Get personalized help
            </p>
          </div>
        </Card>
      </div>

      {/* FAQs */}
      <Card>
        <CardHeader
          title="Frequently Asked Questions"
          description="Quick answers to common questions"
        />
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div
              key={index}
              className="p-4 rounded-xl bg-slate-50 dark:bg-dark-elevated border border-light-border dark:border-dark-border"
            >
              <div className="flex gap-3">
                <QuestionMarkCircleIcon className="h-5 w-5 text-brand-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-slate-900 dark:text-slate-100">
                    {faq.question}
                  </h3>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
                    {faq.answer}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Contact section */}
      <Card className="bg-gradient-to-r from-brand-500 to-purple-500 text-white border-0">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold">Still need help?</h3>
            <p className="mt-1 text-white/80">
              Our support team is here to assist you with any questions.
            </p>
          </div>
          <Button
            variant="secondary"
            className="bg-white/20 hover:bg-white/30 text-white border-white/20"
          >
            Contact Support
          </Button>
        </div>
      </Card>
    </div>
  );
};
