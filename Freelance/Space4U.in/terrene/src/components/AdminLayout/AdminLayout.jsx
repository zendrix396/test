"use client";

import { usePathname } from 'next/navigation';
import Nav from '@/components/Nav/Nav';
import TopBar from '@/components/TopBar/TopBar';
import ConditionalFooter from '@/components/ConditionalFooter/ConditionalFooter';

const AdminLayout = ({ children }) => {
    const pathname = usePathname();
    const isAdminPage = pathname.startsWith('/admin');

    if (isAdminPage) {
        return <>{children}</>;
    }

    return (
        <>
            <TopBar />
            <Nav />
            {children}
            <ConditionalFooter />
        </>
    );
};

export default AdminLayout;
