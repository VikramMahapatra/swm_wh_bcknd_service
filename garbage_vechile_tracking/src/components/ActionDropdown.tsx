import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Phone, MessageCircle, MoreVertical, UserCircle, Building2, Mail } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const getEmailTemplate = (type: "driver" | "vendor", alertType?: string, alertMessage?: string, truckId?: string): { subject: string; body: string } => {
  const subject = `Alert: ${alertType || 'Issue'} - Vehicle ${truckId || 'N/A'}`;
  
  const driverBody = `Dear Driver,

Alert for Vehicle: ${truckId || 'N/A'}
Type: ${alertType || 'Alert'}
Details: ${alertMessage || 'Please check the system for details.'}

Please take immediate action and respond to this alert.

Regards,
Municipal Fleet Management`;

  const vendorBody = `Dear Vendor,

We are notifying you about an alert for your vehicle.

Vehicle: ${truckId || 'N/A'}
Alert Type: ${alertType || 'Alert'}
Details: ${alertMessage || 'Please check the system for details.'}

Please coordinate with the driver and take necessary action.

Regards,
Municipal Fleet Management`;

  return { subject, body: type === 'driver' ? driverBody : vendorBody };
};

interface ActionDropdownProps {
  truckId: string;
  driverName?: string;
  driverPhone?: string;
  driverEmail?: string;
  vendorName?: string;
  vendorPhone?: string;
  vendorEmail?: string;
  alertType?: string;
  alertMessage?: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "icon";
}

const getWhatsAppTemplate = (type: "driver" | "vendor", alertType?: string, alertMessage?: string, truckId?: string): string => {
  const savedTemplate = localStorage.getItem(type === "driver" ? "whatsappDriverTemplate" : "whatsappVendorTemplate");
  
  const defaultDriverTemplate = `Dear Driver,

Alert for Vehicle: {truckId}
Type: {alertType}
Details: {alertMessage}

Please take immediate action and respond to this alert.

Regards,
Municipal Fleet Management`;

  const defaultVendorTemplate = `Dear Vendor,

We are notifying you about an alert for your vehicle.

Vehicle: {truckId}
Alert Type: {alertType}
Details: {alertMessage}

Please coordinate with the driver and take necessary action.

Regards,
Municipal Fleet Management`;

  const template = savedTemplate || (type === "driver" ? defaultDriverTemplate : defaultVendorTemplate);
  
  return template
    .replace(/{truckId}/g, truckId || "N/A")
    .replace(/{alertType}/g, alertType || "Alert")
    .replace(/{alertMessage}/g, alertMessage || "Please check the system for details.");
};

export function ActionDropdown({
  truckId,
  driverName = "Driver",
  driverPhone = "+919876543210",
  driverEmail = "driver@example.com",
  vendorName = "Vendor",
  vendorPhone = "+919876543211",
  vendorEmail = "vendor@example.com",
  alertType,
  alertMessage,
  variant = "outline",
  size = "sm",
}: ActionDropdownProps) {
  const { toast } = useToast();
  const [isOpen, setIsOpen] = useState(false);

  const handleEmailDriver = () => {
    const { subject, body } = getEmailTemplate("driver", alertType, alertMessage, truckId);
    window.open(`mailto:${driverEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, "_self");
    toast({
      title: "Email Opened",
      description: `Opening email client to contact ${driverName}`,
    });
  };

  const handleEmailVendor = () => {
    const { subject, body } = getEmailTemplate("vendor", alertType, alertMessage, truckId);
    window.open(`mailto:${vendorEmail}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`, "_self");
    toast({
      title: "Email Opened",
      description: `Opening email client to contact ${vendorName}`,
    });
  };

  const handleWhatsAppDriver = () => {
    const message = getWhatsAppTemplate("driver", alertType, alertMessage, truckId);
    const encodedMessage = encodeURIComponent(message);
    const phone = driverPhone.replace(/[^0-9]/g, "");
    window.open(`https://wa.me/${phone}?text=${encodedMessage}`, "_blank");
    toast({
      title: "WhatsApp Opened",
      description: `Opening WhatsApp to message ${driverName}`,
    });
  };

  const handleWhatsAppVendor = () => {
    const message = getWhatsAppTemplate("vendor", alertType, alertMessage, truckId);
    const encodedMessage = encodeURIComponent(message);
    const phone = vendorPhone.replace(/[^0-9]/g, "");
    window.open(`https://wa.me/${phone}?text=${encodedMessage}`, "_blank");
    toast({
      title: "WhatsApp Opened",
      description: `Opening WhatsApp to message ${vendorName}`,
    });
  };

  const handleCallDriver = () => {
    window.open(`tel:${driverPhone}`, "_self");
    toast({
      title: "Calling Driver",
      description: `Initiating call to ${driverName}`,
    });
  };

  const handleCallVendor = () => {
    window.open(`tel:${vendorPhone}`, "_self");
    toast({
      title: "Calling Vendor",
      description: `Initiating call to ${vendorName}`,
    });
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant={variant} size={size} className="gap-1">
          <MoreVertical className="h-4 w-4" />
          {size !== "icon" && <span>Actions</span>}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
          Contact Driver
        </div>
        <DropdownMenuItem onClick={handleWhatsAppDriver} className="cursor-pointer">
          <MessageCircle className="h-4 w-4 mr-2 text-green-500" />
          WhatsApp Driver
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleCallDriver} className="cursor-pointer">
          <Phone className="h-4 w-4 mr-2 text-blue-500" />
          Call Driver
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleEmailDriver} className="cursor-pointer">
          <Mail className="h-4 w-4 mr-2 text-orange-500" />
          Email Driver
        </DropdownMenuItem>
        
        <DropdownMenuSeparator />
        
        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
          Contact Vendor
        </div>
        <DropdownMenuItem onClick={handleWhatsAppVendor} className="cursor-pointer">
          <MessageCircle className="h-4 w-4 mr-2 text-green-500" />
          WhatsApp Vendor
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleCallVendor} className="cursor-pointer">
          <Phone className="h-4 w-4 mr-2 text-blue-500" />
          Call Vendor
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleEmailVendor} className="cursor-pointer">
          <Mail className="h-4 w-4 mr-2 text-orange-500" />
          Email Vendor
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
